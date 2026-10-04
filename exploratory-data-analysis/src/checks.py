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
from . import figs_crisis as fc
from . import figs_overview as fo
from . import figs_text as ft
from .config import EVENTS, PROC, RAW, ROOT
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


def phase2_numbers():
    """Numbers quoted in notebook 01 that are not in chart titles."""
    t = fo.load("monthly_totals")
    t["year"] = t.month.dt.year
    show("records per year and subreddit (millions)", (t.pivot_table(index="year", columns=["type", "subreddit"], values="total", aggfunc="sum") / 1e6).round(2).T)
    q = fo.load("raw_quality_monthly")
    q = q[q.type == "comment"].assign(year=lambda d: d.month.dt.year)
    g = q.groupby(["year", "subreddit"])[["raw_rows", "bot_rows", "removed_rows"]].sum()
    show("share of comments removed/deleted and bot, by year", (g[["removed_rows", "bot_rows"]].div(g.raw_rows, axis=0)).unstack().round(3))
    a = fo.load("author_activity")
    grid = np.logspace(-3, 0, 200)
    show("share of messages written by the top 1% of authors", pd.Series({s: float(np.interp(0.01, grid, fo._top_curve(d, grid))) for s, d in a.groupby("subreddit")}).round(3))
    c = fo.load("monthly_totals")
    show("exact comments per submission, 2015 and 2025", c.assign(year=c.month.dt.year).query("year in (2015, 2025)").pivot_table(index=["subreddit", "year"], columns="type", values="total", aggfunc="sum").assign(ratio=lambda d: d.comment / d.submission).round(1))


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


def emoji_concentration(subreddit="teenagers", start="2018-01-01", end="2018-02-01"):
    """How concentrated is the emoji use in the peak month of C14? Total emoji, the top author's and the top five authors' share."""
    from .textmining import EMOJI_RE
    df = _con().execute(f"""
        WITH e AS (SELECT author_id, sum(len(regexp_extract_all(text, '{EMOJI_RE}'))) AS em FROM read_parquet('{PROC}/comment_{subreddit}.parquet')
                   WHERE ts >= '{start}' AND ts < '{end}' GROUP BY 1)
        SELECT sum(em) AS emoji, max(em) AS top1, (SELECT sum(em) FROM (SELECT em FROM e ORDER BY em DESC LIMIT 5)) AS top5, count(*) AS authors FROM e""").df()
    df["top5_share"] = (df.top5 / df.emoji).round(2)
    show(f"emoji concentration, r/{subreddit} {start[:7]}", df)
    return df


def phase3_numbers():
    """Numbers quoted in notebook 02."""
    o = fo.load("overview_counts")
    c = ft._roll(o[(o.type == "comment") & (o.tokens >= 50_000)], "median_tokens")
    c["short_pct"] = c.short_share * 100
    c["short_roll"] = c.groupby("subreddit").short_pct.transform(lambda s: s.rolling(12, min_periods=6).mean())
    rows = []
    for s, d in c.groupby("subreddit"):
        d = d.dropna(subset=["roll"])
        lo = d.loc[d.roll.idxmin()]
        hi = d.loc[d.short_roll.idxmax()]
        rows.append(dict(subreddit=s, first_month=f"{d.month.iloc[0]:%Y-%m}", len_first=d.roll.iloc[0], len_low=lo.roll, low_month=f"{lo.month:%Y-%m}", len_last=d.roll.iloc[-1],
                         short_first=d.short_roll.iloc[0], short_peak=hi.short_roll, short_peak_month=f"{hi.month:%Y-%m}", short_last=d.short_roll.iloc[-1]))
    show("comment length and very short share (12-month means)", pd.DataFrame(rows).round(1).set_index("subreddit"))
    t = fo.load("text_metrics_monthly").assign(y=lambda d: d.month.dt.year)
    show("MTLD and Flesch medians, 2012-14 vs 2024-26", t.groupby("subreddit").apply(lambda d: pd.Series({"mtld_12_14": d[d.y <= 2014].mtld.median(), "mtld_24_26": d[d.y >= 2024].mtld.median(),
                                                                                                          "flesch_12_14": d[d.y <= 2014].flesch_median.median(), "flesch_24_26": d[d.y >= 2024].flesch_median.median()})).round(1))
    tv = ft._roll(t[t.vader_n >= 300].rename(columns={"vader_mean": "v"}), "v")
    rows = []
    for s, d in tv.groupby("subreddit"):
        d = d.dropna(subset=["roll"])
        pk = d.loc[d.roll.idxmax()]
        rows.append(dict(subreddit=s, first=d.roll.iloc[0], peak=pk.roll, peak_month=f"{pk.month:%Y-%m}", last=d.roll.iloc[-1]))
    show("VADER 12-month mean: first, peak, last", pd.DataFrame(rows).round(3).set_index("subreddit"))
    e = fo.load("emoji_monthly")
    e = ft._roll(e[(e.type == "comment") & (e.tokens >= 50_000)], "per_10k_words")
    show("emoji per 10,000 words (12-month mean): max and last", e.groupby("subreddit").roll.agg(["max", "last"]).round(1))
    l = fo.load("lexicon_monthly")
    x = l[(l.type == "comment") & l.tier.isin(["core", "extended"]) & l.enough_tokens].groupby(["subreddit", "month"]).agg(
        h=("hits", "sum"), t=("tokens", "first"), r=("rows_with_hit", "sum"), n=("rows", "first")).reset_index()
    x["per_10k"] = x.h * 1e4 / x.t
    x["reach"] = x.r / x.n
    show("brainrot (core+extended) per 10,000 words: peak month", x.loc[x.groupby("subreddit").per_10k.idxmax()][["subreddit", "month", "per_10k", "reach"]].round(4))
    show("brainrot per 10,000 words: 2025 mean and last six months", pd.DataFrame({"2025": x[x.month.dt.year == 2025].groupby("subreddit").per_10k.mean(), "last6": x[x.month >= "2026-04-01"].groupby("subreddit").per_10k.mean()}).round(2))
    r = x.loc[x.groupby("subreddit").reach.idxmax()][["subreddit", "month", "reach"]]
    r["one_in"] = (1 / r.reach).round(0)
    show("reach: peak", r)
    for tier in ("core", "extended"):
        y = l[(l.type == "comment") & (l.tier == tier) & l.enough_tokens]
        show(f"{tier} tier per 10,000 words: peak month", y.loc[y.groupby("subreddit").per_10k_words.idxmax()][["subreddit", "month", "per_10k_words"]].round(3))
    t2 = fo.load("lexicon_terms_by_year")
    t2 = t2[(t2.type == "comment") & t2.tier.isin(["core", "extended"]) & (t2.year >= 2022)].assign(term=lambda d: d.term.str.replace("-", " "))
    t2["grp"] = t2.term.map(lambda w: w if w in ("skibidi", "rizz", "gyatt", "tung tung", "brain rot", "brainrot") else "rizz" if w.startswith("rizz") else "brain rot" if w.startswith("brain") else "other")
    p = t2.groupby(["year", "grp"]).n.sum().unstack().fillna(0)
    show("term shares by year (%) and hits per year", pd.concat([(p.div(p.sum(axis=1), axis=0) * 100).round(0), p.sum(axis=1).rename("hits")], axis=1))
    wc = fo.load("word_counts_period")
    for g in ("short_form", "long_form"):
        z = ft.log_odds_z(wc, g)
        show(f"log-odds words, {g}", pd.DataFrame({"gained": z.tail(12).index[::-1], "lost": z.head(12).index}))


# ------------------------------------------------------------------ notebook 03 (H4)
def phase4_numbers():
    """Numbers quoted in notebook 03."""
    daily = ev.load_daily()
    rows = []
    for s in fo.ORDER:
        d = daily[daily.subreddit == s].assign(month=lambda x: x.day.dt.to_period("M").dt.to_timestamp())
        g = d.groupby("month")[["hits_crisis", "tokens"]].sum()
        g = g[g.tokens >= 50_000]
        r = g.hits_crisis / g.tokens * 1e4
        sm = r.rolling(3, min_periods=1, center=True).mean()
        rows.append(dict(subreddit=s, peak_month=f"{sm.idxmax():%Y-%m}", peak=sm.max(), median=r.median()))
    show("crisis words per 10,000: 3-month peak and monthly median", pd.DataFrame(rows).round(1).set_index("subreddit"))
    show("event effects (post minus pre) with placebo p, all groups and outcomes", fc.effects_table_cached().round(4))
    d = ev.dense(daily, ["nosurf"])
    show("r/nosurf doomscroll rate (mean per 10,000) and event effects", pd.DataFrame(
        [dict(event=n, effect=ev.real_effect(d, dt, "doom_rate"), p=ev.placebo_p(ev.real_effect(d, dt, "doom_rate"), ev.placebo(d, "doom_rate", EVENTS.values(), n=400)))
         for n, dt in EVENTS.items()]).assign(baseline=ev.ratio(d, "doom_rate", 0, len(d) - 1)).round(3))
    w = fc.load_wui().set_index("month")["wui_global"]
    rows = []
    for g, subs in fc.GROUPS.items():
        for lab, (num, den, sc) in {"sentiment": ("sum_compound", "n", 1), "crisis": ("hits_crisis", "tokens", 1e4)}.items():
            y = fc._monthly_rate(daily, subs, num, den, sc)
            df = pd.concat([w.rename("w"), y.rename("y")], axis=1).dropna()
            dd = df[df.index >= "2013-01-01"].diff().dropna()
            cc = {k: dd.w.corr(dd.y.shift(-k)) for k in range(-6, 7)}
            best = max(cc.items(), key=lambda kv: abs(kv[1]))
            rows.append(dict(group=g, outcome=lab, r_lag0=cc[0], best_lag=best[0], best_r=best[1], n=len(dd), noise_band=1.96 / np.sqrt(len(dd))))
    show("lead-lag with the World Uncertainty Index", pd.DataFrame(rows).round(2))
    ss = fc._sessions_nosurf()
    rows = []
    for name, date in EVENTS.items():
        t0 = pd.Timestamp(date)
        pre = ss[(ss.start >= t0 - pd.Timedelta(days=fc.PRE)) & (ss.start < t0)]
        post = ss[(ss.start >= t0) & (ss.start < t0 + pd.Timedelta(days=fc.POST))]
        rows.append(dict(event=name, sessions_pre=len(pre), sessions_post=len(post), multi_pre=(pre.n_msgs >= 2).mean(), multi_post=(post.n_msgs >= 2).mean(),
                         median_min_pre=pre[pre.n_msgs >= 2].minutes.median(), median_min_post=post[post.n_msgs >= 2].minutes.median()))
    show("r/nosurf sessions around events", pd.DataFrame(rows).round(3))
    rows = []
    for s in fo.ORDER:
        r = fc._monthly_rate(daily, [s], "sum_compound", "n", scale=1)
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


def main(which=None):
    steps = which or ["raw_profile", "spike_context", "phase2_numbers", "emoji_concentration", "phase3_numbers", "phase4_numbers"]
    for s in steps:
        globals()[s]()
    OUT_MD.write_text("# Numbers behind the notebook text\n\nWritten by `python -m src.checks` (numeric tables only; row-level text is never saved).\n\n" + "\n".join(_log))
    print(f"\nwrote {OUT_MD}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
