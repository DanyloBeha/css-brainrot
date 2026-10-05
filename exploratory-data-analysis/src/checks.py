"""Checks and look-ups behind the numbers quoted in the notebook text.

Run `python -m src.checks` to print them and write the numeric ones to docs/numbers_checked.md. Every sentence in the
notebooks that quotes a number not printed in a chart title comes from one of these functions. Functions marked
"row-level" print comment or thread text: they print to the terminal only and are never saved or committed.
"""
import random
import re
import sys

import duckdb
import numpy as np
import pandas as pd

from . import events as ev
from .config import AGG, EVENTS, ORDER, PROC, RAW, ROOT
from .external import load_wui
from .lexicons import BRAINROT_CORE_RE, BRAINROT_EXT_RE, DOOM_RE, SIGMA_RE

OUT_MD = ROOT / "docs" / "numbers_checked.md"
_log = []


def show(title, df):
    """Print a table and keep it for docs/numbers_checked.md."""
    text = df.to_string() if hasattr(df, "to_string") else str(df)
    print(f"\n== {title}\n{text}")
    _log.append(f"### {title}\n\n```\n{text}\n```\n")


def _con():
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con


# ------------------------------------------------------------------ raw data and cleaning (data section of notebook 01)
def raw_profile():
    """First inspection of the raw files: rows per subreddit and type, date range, deleted authors, bots, removed text."""
    con = _con()
    out = []
    for kind, text in (("comments", "body"), ("submissions", "selftext")):
        src = f"read_parquet('{RAW / kind}/*/*/*.parquet', hive_partitioning=false)"
        out.append(con.execute(f"""
            SELECT '{kind}' AS kind, lower(subreddit) AS subreddit, count(*) AS rows, count(DISTINCT id) AS ids,
                   min(make_timestamp(created_utc * 1000000)) AS first, max(make_timestamp(created_utc * 1000000)) AS last,
                   sum((author = '[deleted]')::INT) AS deleted_author, sum((lower(author) LIKE '%bot')::INT) AS bot_suffix,
                   sum(({text} IN ('[deleted]', '[removed]'))::INT) AS removed_text
            FROM {src} GROUP BY ALL ORDER BY ALL""").df())
    show("raw profile", pd.concat(out))
    return pd.concat(out)


def repeated_texts(min_copies=300, top=25):
    """Row-level (terminal only): most repeated comment openings. This is how the moderator templates were found."""
    con = _con()
    df = con.execute(f"""
        SELECT left(body, 70) AS opening, count(*) AS copies, count(DISTINCT author) AS authors, max((distinguished = 'moderator')::INT) AS moderator
        FROM read_parquet('{RAW / "comments"}/*/*/*.parquet', hive_partitioning=false) WHERE length(body) >= 40
        GROUP BY 1 HAVING count(*) >= {min_copies} ORDER BY copies DESC LIMIT {top}""").df()
    print("\n== most repeated comment openings (row-level, not saved)\n", df.to_string())
    return df


def spam_candidates(top=10):
    """Row-level (terminal only): the longest comments with the fewest distinct words in the cleaned data's raw source."""
    con = _con()
    df = con.execute(f"""
        SELECT subreddit, year(make_timestamp(created_utc * 1000000)) AS year, count(*) AS comments, count(DISTINCT author) AS authors,
               max(length(body)) AS max_chars, left(min(body), 60) AS opening
        FROM read_parquet('{RAW / "comments"}/*/*/*.parquet', hive_partitioning=false)
        WHERE body ILIKE 'fuck fuck fuck%' GROUP BY ALL ORDER BY comments DESC LIMIT {top}""").df()
    print("\n== repetitive 'fuck fuck' bursts (row-level, not saved)\n", df.to_string())
    return df


# ------------------------------------------------------------------ notebook 01 (overview and activity)
def spike_context(days=("2020-04-15", "2021-02-12", "2021-12-30", "2024-01-25", "2024-03-22", "2024-08-16", "2024-12-19", "2025-09-11")):
    """Why were these r/nosurf days busy? Threads per day, share of the biggest thread and of the top three (numbers are saved);
    the titles of the two biggest threads are printed to the terminal only (row-level)."""
    con = _con()
    q = f"""
        WITH c AS (SELECT ts::date AS d, link_id, count(*) AS n FROM read_parquet('{PROC}/comment_nosurf.parquet') GROUP BY 1, 2),
        r AS (SELECT *, row_number() OVER (PARTITION BY d ORDER BY n DESC) AS rk FROM c)
        SELECT d, sum(n) AS comments, count(*) AS threads, max(n) AS top1, round(max(n) / sum(n), 2) AS top1_share,
               round(sum(n) FILTER (WHERE rk <= 3) / sum(n), 2) AS top3_share
        FROM r GROUP BY d"""
    df = con.execute(q).df()
    df["d"] = pd.to_datetime(df["d"])
    typical = df[df.d >= "2020-01-01"][["comments", "threads", "top1_share", "top3_share"]].median()
    sel = df[df.d.dt.strftime("%Y-%m-%d").isin(days)].sort_values("d")
    show("r/nosurf spike days (typical day = median since 2020 in the last row)", pd.concat([sel, pd.DataFrame([{"d": "typical", **typical.to_dict()}])]))
    for day in days:
        r = con.execute(f"""
            WITH c AS (SELECT link_id, count(*) AS n FROM read_parquet('{PROC}/comment_nosurf.parquet') WHERE ts::date = '{day}' GROUP BY 1 ORDER BY 2 DESC LIMIT 2),
            s AS (SELECT 't3_' || id AS link_id, title FROM read_parquet('{RAW / "submissions"}/subreddit=nosurf/*/*.parquet', hive_partitioning=false))
            SELECT c.n, s.title FROM c LEFT JOIN s USING (link_id)""").fetchall()
        print(day, [(n, (t or "(post not in sample)")[:90]) for n, t in r])
    return sel


# ------------------------------------------------------------------ notebook 02 (text)
def lexicon_spot_check(n=50, seed=42):
    """Row-level (terminal only): random matches in context per lexicon tier, as used for the hand check (50 per tier read by one
    person; this draw is reproducible but is not the exact draw that was read, because the lexicon was tightened afterwards)."""
    from .textmining import MATCHES
    df = _con().execute(f"""SELECT year(ts) AS y, subreddit, text, core_terms, ext_terms, sigma_terms, doom_terms FROM read_parquet('{MATCHES}')""").df()
    rng = random.Random(seed)
    for col, rx, k in (("core_terms", BRAINROT_CORE_RE, n), ("ext_terms", BRAINROT_EXT_RE, n), ("sigma_terms", SIGMA_RE, 30), ("doom_terms", DOOM_RE, 20)):
        sub = df[df[col].map(len) > 0]
        print(f"\n== {col}: {len(sub)} rows, showing {k} (row-level, not saved)")
        for i in rng.sample(range(len(sub)), min(k, len(sub))):
            r = sub.iloc[i]
            m = re.search(rx, r.text.lower().replace("’", "'"))
            if m:
                a = max(0, m.start() - 50)
                print(f"[{r.y} {r.subreddit[:5]}] ...{r.text[a:m.end() + 50]!r}")


# ------------------------------------------------------------------ notebook 03 (H4)
def phase4_numbers():
    """Numbers quoted in notebook 03."""
    daily = ev.load_daily()
    rows = []
    for s in ORDER:
        d = daily[daily.subreddit == s].assign(month=lambda x: x.day.dt.to_period("M").dt.to_timestamp())
        g = d.groupby("month")[["hits_crisis", "tokens"]].sum()
        g = g[g.tokens >= 50_000]
        r = g.hits_crisis / g.tokens * 1e4
        sm = r.rolling(3, min_periods=1, center=True).mean()
        rows.append(dict(subreddit=s, peak_month=f"{sm.idxmax():%Y-%m}", peak=sm.max(), median=r.median()))
    show("crisis words per 10,000: 3-month peak and monthly median", pd.DataFrame(rows).round(1).set_index("subreddit"))
    show("event effects (post minus pre) with placebo p, all groups and outcomes", ev.effects_table_cached().round(4))
    d = ev.dense(daily, ["nosurf"])
    show("r/nosurf doomscroll rate (mean per 10,000) and event effects", pd.DataFrame(
        [dict(event=n, effect=ev.real_effect(d, dt, "doom_rate"), p=ev.placebo_p(ev.real_effect(d, dt, "doom_rate"), ev.placebo(d, "doom_rate", EVENTS.values(), n=400)))
         for n, dt in EVENTS.items()]).assign(baseline=ev.ratio(d, "doom_rate", 0, len(d) - 1)).round(3))
    w = load_wui().set_index("month")["wui_global"]
    rows = []
    for g, subs in ev.GROUPS.items():
        for lab, (num, den, sc) in {"sentiment": ("sum_compound", "n", 1), "crisis": ("hits_crisis", "tokens", 1e4)}.items():
            y = ev.monthly_rate(daily, subs, num, den, sc)
            df = pd.concat([w.rename("w"), y.rename("y")], axis=1).dropna()
            dd = df[df.index >= "2013-01-01"].diff().dropna()
            cc = {k: dd.w.corr(dd.y.shift(-k)) for k in range(-6, 7)}
            best = max(cc.items(), key=lambda kv: abs(kv[1]))
            rows.append(dict(group=g, outcome=lab, r_lag0=cc[0], best_lag=best[0], best_r=best[1], n=len(dd), noise_band=1.96 / np.sqrt(len(dd))))
    show("lead-lag with the World Uncertainty Index", pd.DataFrame(rows).round(2))
    ss = ev.nosurf_sessions()
    rows = []
    for name, date in EVENTS.items():
        t0 = pd.Timestamp(date)
        pre = ss[(ss.start >= t0 - pd.Timedelta(days=ev.PRE)) & (ss.start < t0)]
        post = ss[(ss.start >= t0) & (ss.start < t0 + pd.Timedelta(days=ev.POST))]
        rows.append(dict(event=name, sessions_pre=len(pre), sessions_post=len(post), multi_pre=(pre.n_msgs >= 2).mean(), multi_post=(post.n_msgs >= 2).mean(),
                         median_min_pre=pre[pre.n_msgs >= 2].minutes.median(), median_min_post=post[post.n_msgs >= 2].minutes.median()))
    show("r/nosurf sessions around events", pd.DataFrame(rows).round(3))
    rows = []
    for s in ORDER:
        r = ev.monthly_rate(daily, [s], "sum_compound", "n", scale=1)
        r = r[r.index >= ("2016-01-01" if s == "nosurf" else "2013-01-01")]
        rows.append(dict(subreddit=s, change_points=", ".join(f"{b:%Y-%m}" for b in ev.changepoints(r))))
    show("change-points in monthly VADER", pd.DataFrame(rows).set_index("subreddit"))


def youtube_trending_profile(countries=("US", "GB", "CA", "IN")):
    """What the Kaggle YouTube trending files hold: coverage, unique videos, brainrot-titled videos (with and without the Roblox game
    "Steal a Brainrot") per publish quarter, for the rsrishav files (2020-2024) and the keshavbansal95 file (2024-25).
    Also writes data/external/youtube_trending_monthly.parquet."""
    from .external import trending_monthly, trending_videos, trending_videos_2024_25
    rows = []
    for c in countries:
        v = trending_videos(c)
        rows.append(dict(source="rsrishav", unit=c, rows=v.attrs["rows"], videos=len(v), trending_first=v.attrs["trending_first"].date(), trending_last=v.attrs["trending_last"].date(),
                         brainrot_videos=int(v.brainrot.sum())))
    k = trending_videos_2024_25()
    rows.append(dict(source="keshavbansal95", unit=f"{int(k.countries.max())} max countries per video", rows=len(k), videos=len(k), trending_first=k["trending"].min().date(),
                     trending_last=k["trending"].max().date(), brainrot_videos=int(k.brainrot.sum())))
    show("YouTube trending files: coverage and brainrot-titled videos", pd.DataFrame(rows).set_index(["source", "unit"]))
    m = trending_monthly(countries)
    m["quarter"] = m["month"].dt.to_period("Q")
    q = m.groupby(["source", "quarter"]).agg(videos=("videos", "sum"), brainrot=("brainrot_videos", "sum"), excl_game=("brainrot_excl_game", "sum"))
    q["per_1000"] = q.brainrot / q.videos * 1000
    q["per_1000_excl_game"] = q.excl_game / q.videos * 1000
    show("YouTube trending: unique brainrot-titled videos per publish quarter", q[q.brainrot > 0].round(2))


def brainrot_event_check(subs=None):
    """Brainrot terms around the events: per term group and event, rate per 10,000 words in the 8 weeks before and the 4 weeks after,
    the change, hits after and the placebo p-value. subs=None pools all six subreddits; pass ["memes", "teenagers"] for short-form."""
    df = ev.term_event_effects(subs)
    label = ", ".join(subs) if subs else "pooled six subreddits"
    show(f"brainrot terms around events, per 10,000 words ({label})", df.round(3).set_index(["event", "term"]))
    return df


def brainrot_event_check_shortform():
    return brainrot_event_check(["memes", "teenagers"])


def volume_event_check():
    """Exact comments per day (monthly totals divided by days in the month) of r/memes + r/teenagers: mean of the 3 months before the event
    month vs the 3 months after it, per event. Monthly resolution cannot show effects that last days."""
    t = pd.read_parquet(AGG / "monthly_totals.parquet")
    t = t[t.subreddit.isin(["memes", "teenagers"]) & (t.type == "comment")]
    per_day = t.assign(v=t.total / t.month.dt.days_in_month).groupby("month")["v"].sum()
    rows = []
    for name, date in EVENTS.items():
        m0 = pd.Timestamp(date).to_period("M").to_timestamp()
        before = per_day[(per_day.index >= m0 - pd.DateOffset(months=3)) & (per_day.index < m0)].mean()
        after = per_day[(per_day.index > m0) & (per_day.index <= m0 + pd.DateOffset(months=3))].mean()
        rows.append(dict(event=name, before=before, after=after, change_pct=(after / before - 1) * 100))
    show("short-form comments per day: 3 months before vs 3 months after the event month", pd.DataFrame(rows).round(1).set_index("event"))


def brainrot_spike_check(months=("2023-10-01", "2023-11-01", "2024-04-01", "2024-12-01", "2025-01-01")):
    """What the brainrot spikes of r/memes + r/teenagers (monthly rate per 10,000 words) are made of: the top months, the terms behind the chosen
    months, how many of the matching comments mention a crisis topic or TikTok, and the crisis-word rate of the same subreddits (monthly,
    median of all months for comparison). Answers whether the later spikes came with a crisis; exploratory, the events were not chosen in advance."""
    sh = ["memes", "teenagers"]
    tt = pd.read_parquet(AGG / "lexicon_terms_by_month.parquet")
    tt = tt[(tt.type == "comment") & tt.tier.isin(["core", "extended"]) & tt.subreddit.isin(sh)]
    ov = pd.read_parquet(AGG / "overview_counts.parquet")
    tok = ov[(ov.type == "comment") & ov.subreddit.isin(sh)].groupby("month")["tokens"].sum()
    rate = (tt.groupby("month")["n"].sum() / tok * 1e4).dropna()
    show("brainrot per 10,000 words (memes + teenagers): top months", rate.sort_values(ascending=False).head(6).round(2))
    by = tt.groupby(["month", "term"])["n"].sum().unstack().fillna(0)
    show("top terms (hits) in the chosen months", pd.DataFrame({m[:7]: by.loc[m].sort_values(ascending=False).head(4).astype(int).to_dict() for m in months}).T)
    kw = {"gaza/israel/palestine/hamas": "israel|gaza|palestin|hamas", "war": r"\bwars?\b", "iran": "iran", "tiktok": "tiktok|tik tok", "ban": r"\bban(ned)?\b",
          "oxford/word of the year": "oxford|word of the year"}
    base = f"""SELECT date_trunc('month', ts) m, lower(text) t FROM read_parquet('{PROC}/derived/lexicon_matches.parquet')
               WHERE type = 'comment' AND subreddit IN ('memes', 'teenagers') AND (len(core_terms) > 0 OR len(ext_terms) > 0)"""
    rows = []
    for m in months:
        r = {"month": m[:7], "hit comments": duckdb.sql(f"SELECT count(*) FROM ({base}) WHERE m = timestamp '{m}'").fetchone()[0]}
        for k, pat in kw.items():
            r[k] = duckdb.sql(f"SELECT count(*) FROM ({base}) WHERE m = timestamp '{m}' AND regexp_matches(t, '{pat}')").fetchone()[0]
        rows.append(r)
    show("brainrot-hit comments mentioning a topic, chosen months", pd.DataFrame(rows).set_index("month"))
    d = ev.load_daily()
    x = d[d.subreddit.isin(sh)].assign(month=lambda z: z.day.dt.to_period("M").dt.to_timestamp()).groupby("month")[["hits_crisis", "tokens"]].sum()
    cr = x.hits_crisis / x.tokens * 1e4
    show(f"crisis words per 10,000 (memes + teenagers), 2023-08 to 2025-02 (median of all months {cr.median():.1f})", cr["2023-08":"2025-02"].round(1))


def doomscroll_trend_check():
    """r/nosurf doomscroll mentions per 10,000 words: per year, and the latest 4-week rolling rate (complete data, weekly resolution is valid)."""
    d = ev.load_daily()
    d = d[d.subreddit == "nosurf"].set_index("day")[["hits_doom", "tokens"]]
    yr = d.groupby(d.index.year).sum()
    show("r/nosurf doomscroll mentions per 10,000 words, by year", (yr.hits_doom / yr.tokens * 1e4).round(2).loc[2019:])
    w = d.resample("W").sum()
    r = w.hits_doom.rolling(4).sum() / w.tokens.rolling(4).sum() * 1e4
    show("r/nosurf doomscroll, 4-week rolling rate: latest and maximum", pd.Series({"latest": r.iloc[-1], "max": r.max(), "max_week": str(r.idxmax().date())}))


def rhythm_check(n_fake=150):
    """r/nosurf hour-by-weekday comment share, 4 weeks after minus 8 weeks before each event: the largest single-cell shift, and the
    95th percentile of that largest shift at random fake dates (the null result mentioned in the H4 text; the chart was removed)."""
    df = ev.nosurf_comments()
    ts = df["ts"]
    rng = np.random.default_rng(42)
    real = [pd.Timestamp(v) for v in EVENTS.values()]
    ok = [d for d in pd.date_range("2018-01-01", "2026-07-15") if all(abs((d - r).days) > 120 for r in real)]

    def shift(t0):
        def mat(lo, hi):
            m = np.zeros((7, 24))
            sel = ts[(ts >= lo) & (ts < hi)]
            for dow, hr in zip(sel.dt.dayofweek.to_numpy(), sel.dt.hour.to_numpy()):
                m[dow, hr] += 1
            m = m / m.sum() * 100
            return (np.roll(m, 1, 1) + m + np.roll(m, -1, 1)) / 3
        return np.abs(mat(t0, t0 + pd.Timedelta(days=ev.POST)) - mat(t0 - pd.Timedelta(days=ev.PRE), t0)).max()
    ref = np.percentile([shift(ok[i]) for i in rng.choice(len(ok), n_fake, replace=False)], 95)
    show("r/nosurf daily rhythm: largest cell shift per event (pp) and the 95th percentile at random dates",
         pd.Series({**{k: round(shift(pd.Timestamp(v)), 2) for k, v in EVENTS.items()}, "95% of random dates stay under": round(ref, 2)}))


def session_bucket_check():
    """r/nosurf sessions of 2+ messages by length bucket (share in %), 8 weeks before vs 4 weeks after each event."""
    ss = ev.nosurf_sessions()
    bk = [(1, 1, "1 min"), (2, 4, "2-4"), (5, 9, "5-9"), (10, 29, "10-29"), (30, 1e9, "30+")]
    rows = []
    for name, date in EVENTS.items():
        t0 = pd.Timestamp(date)
        a = ss[(ss.start >= t0 - pd.Timedelta(days=ev.PRE)) & (ss.start < t0) & (ss.n_msgs >= 2)]["minutes"].clip(lower=1).to_numpy()
        b = ss[(ss.start >= t0) & (ss.start < t0 + pd.Timedelta(days=ev.POST)) & (ss.n_msgs >= 2)]["minutes"].clip(lower=1).to_numpy()
        for lo, hi, lab in bk:
            rows.append(dict(event=name, bucket=lab, before=((a >= lo) & (a <= hi)).mean() * 100, after=((b >= lo) & (b <= hi)).mean() * 100))
    df = pd.DataFrame(rows).round(1)
    show("r/nosurf sessions (2+ messages): share by length bucket, before vs after", df.pivot(index="event", columns="bucket", values=["before", "after"]))


def authors_check():
    """Same r/nosurf authors before and after each event: number of authors, mean change in tone, 95% bootstrap interval, and the 95% range
    of the mean change at random fake dates."""
    D, CI, lo, hi = ev.authors_stats()
    rows = [dict(event=n, authors=len(D[n]), mean_change=D[n].mean(), ci_low=CI[n][0], ci_high=CI[n][1]) for n in EVENTS]
    show(f"same r/nosurf authors: change in mean tone (random-date 95% range {lo:+.3f} to {hi:+.3f})", pd.DataFrame(rows).round(3).set_index("event"))


def session_shift_check():
    """Largest length-bucket shift of r/nosurf sessions per event and its placebo p-value (same statistic at 100 random fake dates)."""
    st = ev.session_stats()
    rows = [dict(event=n, bucket=st["big"][n][2], before=st["big"][n][0], after=st["big"][n][1], gap=abs(st["big"][n][1] - st["big"][n][0])) for n in EVENTS]
    df = pd.DataFrame(rows).round(1).set_index("event")
    show(f"r/nosurf sessions: bucket that moved most per event (largest gap {st['gap']:.1f} points after {st['top']}, placebo p = {st['p']:.2f}; "
         f"largest gap at the other events {st['others']:.1f})", df)


def main(which=None):
    steps = which or ["raw_profile", "spike_context", "phase4_numbers",
                      "brainrot_event_check", "brainrot_event_check_shortform", "volume_event_check", "brainrot_spike_check", "doomscroll_trend_check",
                      "rhythm_check", "session_bucket_check", "authors_check", "session_shift_check"]
    for s in steps:
        globals()[s]()
    OUT_MD.write_text("# Numbers behind the notebook text\n\nWritten by `python -m src.checks` (numeric tables only; row-level text is never saved).\n\n" + "\n".join(_log))
    print(f"\nwrote {OUT_MD}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
