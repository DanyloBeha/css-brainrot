"""H4: event study, placebo test, change-points on top of the per-comment features.

Design notes (see docs/research_log.md): the data are time-slot samples, so daily values for the big subreddits are
sparse. We therefore (1) work with sums per day (sums add up correctly over any window) and compute ratio-of-sums per
window, never with a mean of daily means, and (2) judge an effect against a placebo distribution at random fake dates
instead of a textbook standard error.
"""
import duckdb
import numpy as np
import pandas as pd
import polars as pl

from .config import AGG, EVENTS, PROC
from .config import GROUPS as ALL_GROUPS
from .sessions import sessions

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


TERM_GROUPS = ["rizz", "skibidi", "gyatt", "brain rot", "tung tung", "mewing"]


def term_group(word):
    w = word.replace("-", " ")
    return "rizz" if w.startswith("rizz") else "brain rot" if w.startswith("brain") else w


def term_daily(subs=None):
    """Daily brainrot-term hits per term group (comments only) and daily words, for the chosen subreddits (None = all six).
    Returns (hits DataFrame with one column per term group, words Series), both indexed by every day 2012-01-01 .. 2026-09-30."""
    from .config import AGG
    full = pd.date_range("2012-01-01", "2026-09-30")
    t = pd.read_parquet(AGG / "lexicon_terms_daily.parquet")
    t = t[(t.type == "comment") & t.tier.isin(["core", "extended"])]
    if subs:
        t = t[t.subreddit.isin(subs)]
    t = t.assign(grp=t["term"].map(term_group))
    hits = t.groupby(["day", "grp"])["n"].sum().unstack().reindex(full, fill_value=0).reindex(columns=TERM_GROUPS).fillna(0)
    daily = load_daily()
    if subs:
        daily = daily[daily.subreddit.isin(subs)]
    words = daily.groupby("day")["tokens"].sum().reindex(full, fill_value=0)
    return hits, words


def term_event_effects(subs=None, n_fake=300, seed=42, pre=56, post=28):
    """Per term group and event: rate per 10,000 words before (8 weeks) and after (4 weeks), the change, hits after, and the placebo
    p-value (same change at random fake dates at least 120 days from any event, from 2022-11 on, when the vocabulary exists)."""
    from .config import EVENTS
    hits, words = term_daily(subs)
    full = hits.index
    cw = np.r_[0, words.to_numpy().cumsum()]
    rng = np.random.default_rng(seed)
    real = [pd.Timestamp(v) for v in EVENTS.values()]
    pool = [d for d in pd.date_range("2022-11-01", "2026-08-01") if all(abs((d - r).days) > 120 for r in real)]
    rows = []
    for g in TERM_GROUPS:
        ch = np.r_[0, hits[g].to_numpy().cumsum()]

        def eff(i0):
            rate = lambda a, b: (ch[b + 1] - ch[a]) / max(cw[b + 1] - cw[a], 1) * 1e4
            return rate(i0, i0 + post - 1) - rate(i0 - pre, i0 - 1), rate(i0 - pre, i0 - 1), rate(i0, i0 + post - 1)
        fake = np.array([eff(full.get_loc(pool[j]))[0] for j in rng.choice(len(pool), n_fake, replace=False)])
        for name, date in EVENTS.items():
            i0 = full.get_loc(pd.Timestamp(date))
            change, before, after = eff(i0)
            rows.append(dict(term=g, event=name, pre=before, post=after, change=change, hits_post=int(ch[i0 + post] - ch[i0]),
                             placebo_p=float((np.abs(fake) >= abs(change)).mean())))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- H4 helpers used by the notebook charts and by src/checks.py
GROUPS = {k: ALL_GROUPS[k] for k in ("short_form", "long_form", "baseline", "reflective")}      # the four communities of the H4 design
EV_NAMES = list(EVENTS)
PRE, POST = 56, 28                                                                             # days before / after an event


def monthly_rate(daily, subs, num, den, scale=1e4):
    d = daily[daily.subreddit.isin(subs)].assign(month=lambda x: x.day.dt.to_period("M").dt.to_timestamp())
    g = d.groupby("month")[[num, den]].sum()
    return g[num] / g[den] * scale


def effects_table(n=400):
    """Post-minus-pre effects at the four events and placebo p-values, per group and outcome."""
    daily = load_daily()
    rows = []
    for g, subs in GROUPS.items():
        d = dense(daily, subs)
        for name, date in EVENTS.items():
            for oc in ("sentiment", "neg_share", EVENT_OUTCOME[name], "crisis_rate"):
                real = real_effect(d, date, oc)
                fake = placebo(d, oc, EVENTS.values(), n=n)
                rows.append(dict(group=g, event=name, outcome=oc, effect=real, placebo_sd=np.nanstd(fake), p=placebo_p(real, fake),
                                 placebo_lo=np.nanpercentile(fake, 2.5), placebo_hi=np.nanpercentile(fake, 97.5)))
    df = pd.DataFrame(rows)
    df.to_parquet(AGG / "event_effects.parquet", index=False)
    return df


def effects_table_cached():
    p = AGG / "event_effects.parquet"
    return pd.read_parquet(p) if p.exists() else effects_table()


def nosurf_comments():
    return duckdb.sql(f"""
        SELECT f.id, f.ts, f.compound, p.author_id FROM read_parquet('{PROC}/derived/features_nosurf.parquet') f
        JOIN read_parquet('{PROC}/comment_nosurf.parquet') p USING (id)""").df()


def nosurf_sessions():
    lf = pl.concat([pl.scan_parquet(PROC / "comment_nosurf.parquet").select("author_id", "ts"),
                    pl.scan_parquet(PROC / "submission_nosurf.parquet").select("author_id", "ts")])
    return sessions(lf).collect().to_pandas()


BUCKETS = [(1, 1, "1 min"), (2, 4, "2-4"), (5, 9, "5-9"), (10, 29, "10-29"), (30, 1e9, "30+")]


def session_stats(n_fake=100):
    """r/nosurf sessions of 2+ messages around each event: windows, medians, the length bucket that moved most for each event, and a
    placebo for the largest bucket shift (same statistic at random fake dates). Used by C24 and by src/checks.py."""
    s = nosurf_sessions()

    def windows(t0):
        a = s[(s.start >= t0 - pd.Timedelta(days=PRE)) & (s.start < t0) & (s.n_msgs >= 2)]["minutes"].clip(lower=1).to_numpy()
        b = s[(s.start >= t0) & (s.start < t0 + pd.Timedelta(days=POST)) & (s.n_msgs >= 2)]["minutes"].clip(lower=1).to_numpy()
        return a, b

    def shares(a, b):
        return [(((a >= lo) & (a <= hi)).mean() * 100, ((b >= lo) & (b <= hi)).mean() * 100, lab) for lo, hi, lab in BUCKETS]

    W, med, big = {}, {}, {}
    for n in EV_NAMES:
        a, b = windows(pd.Timestamp(EVENTS[n]))
        W[n], med[n] = (a, b), (np.median(a), np.median(b))
        big[n] = max(shares(a, b), key=lambda r: abs(r[1] - r[0]))                # the bucket that moved most for this event
    rng = np.random.default_rng(42)
    realev = [pd.Timestamp(v) for v in EVENTS.values()]
    ok = [d for d in pd.date_range("2018-01-01", "2026-07-15") if all(abs((d - r).days) > 120 for r in realev)]
    fake = np.array([max(abs(r[1] - r[0]) for r in shares(*windows(ok[i]))) for i in rng.choice(len(ok), n_fake, replace=False)])
    top_n = max(EV_NAMES, key=lambda n: abs(big[n][1] - big[n][0]))
    gap = abs(big[top_n][1] - big[top_n][0])
    others = max(abs(big[n][1] - big[n][0]) for n in EV_NAMES if n != top_n)
    return dict(W=W, med=med, big=big, top=top_n, gap=gap, others=others, p=float((fake >= gap).mean()), shares=shares)


def authors_stats(n_boot=500, n_fake=120):
    """Per-author change in mean tone (4 weeks after vs 8 weeks before) for authors present in both windows, bootstrap intervals of the
    mean, and the 95% range of the mean change at random fake dates. Used by C26 and by src/checks.py."""
    df = nosurf_comments()
    df = df[df.author_id.notna()]
    rng = np.random.default_rng(42)

    def change(t0):
        pre = df[(df.ts >= t0 - pd.Timedelta(days=PRE)) & (df.ts < t0)].groupby("author_id").compound.mean()
        post = df[(df.ts >= t0) & (df.ts < t0 + pd.Timedelta(days=POST))].groupby("author_id").compound.mean()
        both = pre.index.intersection(post.index)
        return (post[both] - pre[both]).to_numpy()

    real = [pd.Timestamp(v) for v in EVENTS.values()]
    ok = [d for d in pd.date_range("2018-01-01", "2026-07-15") if all(abs((d - r).days) > 120 for r in real)]
    fake = np.array([change(ok[i]).mean() for i in rng.choice(len(ok), n_fake, replace=False)])
    lo_f, hi_f = np.percentile(fake, [2.5, 97.5])
    D = {n: change(pd.Timestamp(EVENTS[n])) for n in EV_NAMES}
    CI = {n: np.percentile([rng.choice(D[n], len(D[n])).mean() for _ in range(n_boot)], [2.5, 97.5]) for n in EV_NAMES}
    return D, CI, lo_f, hi_f
