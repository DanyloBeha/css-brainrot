"""H4: event study, placebo test, change-points on top of the per-comment features.

Design notes (see docs/research_log.md): the data are time-slot samples, so daily values for the big subreddits are
sparse. We therefore (1) work with sums per day (sums add up correctly over any window) and compute ratio-of-sums per
window, never with a mean of daily means, and (2) judge an effect against a placebo distribution at random fake dates
instead of a textbook standard error.
"""
import duckdb
import numpy as np
import pandas as pd

from .config import AGG, PROC

FEAT = PROC / "derived"
OUTCOMES = {                      # outcome -> (numerator column, denominator column)
    "sentiment": ("sum_compound", "n"),
    "neg_share": ("n_neg", "n"),
    "crisis_rate": ("hits_crisis", "tokens"),
    "doom_rate": ("hits_doom", "tokens"),
    "covid_rate": ("hits_covid", "tokens"),
    "ukraine_rate": ("hits_ukraine", "tokens"),
    "gaza_rate": ("hits_gaza", "tokens"),
    "kirk_rate": ("hits_kirk", "tokens"),
}
PER_10K = {"crisis_rate", "doom_rate", "covid_rate", "ukraine_rate", "gaza_rate", "kirk_rate"}
EVENT_OUTCOME = {"COVID-19 pandemic declared": "covid_rate", "Russia full-scale invasion of Ukraine": "ukraine_rate",
                 "Hamas attack / Gaza war begins": "gaza_rate", "Assassination of Charlie Kirk": "kirk_rate"}


def build_daily():
    """Per subreddit x day: number of comments, summed VADER, negatives, words and lexicon hits (sums, so any window can be formed)."""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    df = con.execute(f"""
        SELECT subreddit, CAST(date_trunc('day', ts) AS DATE) AS day, count(*) AS n, sum(compound) AS sum_compound,
               sum((compound <= -0.05)::INT) AS n_neg, sum((compound <= -0.5)::INT) AS n_very_neg, sum(n_tokens) AS tokens,
               sum(hits_crisis) AS hits_crisis, sum(hits_covid) AS hits_covid, sum(hits_ukraine) AS hits_ukraine,
               sum(hits_gaza) AS hits_gaza, sum(hits_kirk) AS hits_kirk, sum(hits_doom) AS hits_doom,
               count(DISTINCT slot_start) AS slots
        FROM read_parquet('{FEAT}/features_*.parquet') GROUP BY ALL ORDER BY ALL""").df()
    df["day"] = pd.to_datetime(df["day"])
    df.to_parquet(AGG / "daily_features.parquet", index=False)
    print(f"daily_features: {len(df):,} rows")
    return df


def load_daily():
    return pd.read_parquet(AGG / "daily_features.parquet")


def dense(daily, subs):
    """Daily sums for a set of subreddits added together, one row per calendar day (missing days = 0)."""
    d = daily[daily.subreddit.isin(subs)].drop(columns="subreddit").groupby("day").sum()
    full = pd.date_range("2012-01-01", "2026-09-30", freq="D")
    return d.reindex(full, fill_value=0)


def ratio(d, outcome, lo, hi):
    """Ratio-of-sums of an outcome over days [lo, hi] (inclusive) given as day offsets from the event date in `d` (cum sums)."""
    num, den = OUTCOMES[outcome]
    a = d[num].iloc[lo:hi + 1].sum()
    b = d[den].iloc[lo:hi + 1].sum()
    scale = 1e4 if outcome in PER_10K else 1
    return np.nan if b == 0 else a / b * scale


def effect(cum, i0, outcome, pre=56, post=28):
    """Post-minus-pre difference around day index i0. `cum` = cumulative sums with a leading zero row."""
    num, den = OUTCOMES[outcome]
    def r(a, b):
        den_v = cum[den][b + 1] - cum[den][a]
        return np.nan if den_v == 0 else (cum[num][b + 1] - cum[num][a]) / den_v
    scale = 1e4 if outcome in PER_10K else 1
    return (r(i0, i0 + post - 1) - r(i0 - pre, i0 - 1)) * scale


def _cum(d):
    out = {}
    for c in set(sum(([a, b] for a, b in OUTCOMES.values()), [])):
        out[c] = np.r_[0, d[c].to_numpy().cumsum()]
    return out


def event_curve(d, event, outcome, pre_weeks=8, post_weeks=12):
    """Weekly ratio-of-sums in event time (week 0 = days 0..6 from the event), minus the pre-event mean."""
    i0 = d.index.get_loc(pd.Timestamp(event))
    rows = []
    for k in range(-pre_weeks, post_weeks):
        lo, hi = i0 + 7 * k, i0 + 7 * k + 6
        rows.append((k, ratio(d, outcome, lo, hi), d["n"].iloc[lo:hi + 1].sum()))
    c = pd.DataFrame(rows, columns=["week", "value", "n"]).set_index("week")
    base = ratio(d, outcome, i0 - 7 * pre_weeks, i0 - 1)
    c["delta"] = c["value"] - base
    return c


def placebo(d, outcome, real_events, n=400, pre=56, post=28, seed=42, min_n=300, buffer=120):
    """Same post-minus-pre statistic at random fake dates away from every real event."""
    cum = _cum(d)
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2013-03-01", "2026-08-01", freq="D")
    real = [pd.Timestamp(e) for e in real_events]
    ok = [t for t in idx if all(abs((t - r).days) > buffer for r in real)]
    out = []
    for j in rng.permutation(len(ok)):
        i0 = d.index.get_loc(ok[j])
        if d["n"].iloc[i0:i0 + post].sum() < min_n or d["n"].iloc[i0 - pre:i0].sum() < min_n:
            continue
        out.append(effect(cum, i0, outcome, pre, post))
        if len(out) == n:
            break
    return np.array(out)


def real_effect(d, event, outcome, pre=56, post=28):
    return effect(_cum(d), d.index.get_loc(pd.Timestamp(event)), outcome, pre, post)


def placebo_p(real, fake):
    """Two-sided share of placebo effects at least as large (in absolute value) as the real one."""
    fake = fake[~np.isnan(fake)]
    return float((np.abs(fake) >= abs(real)).mean())


def changepoints(series, min_size=6, penalty_scale=3.0):
    """Change-points (PELT, least-squares cost) in a monthly series; penalty from the noise of month-to-month differences."""
    import ruptures as rpt
    y = series.dropna()
    sig = 1.4826 * np.median(np.abs(np.diff(y.to_numpy()) - np.median(np.diff(y.to_numpy())))) / np.sqrt(2)
    pen = penalty_scale * sig ** 2 * np.log(len(y))
    bk = rpt.Pelt(model="l2", min_size=min_size, jump=1).fit(y.to_numpy().reshape(-1, 1)).predict(pen=pen)
    return [y.index[b] for b in bk[:-1]]
