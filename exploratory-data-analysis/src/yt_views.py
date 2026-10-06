# per-video numbers of the scraped YouTube sample, no ids/titles/channels: tracked, so the chart runs without the scrape
import sqlite3

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .config import AGG, EXT, ROOT

SCRAPE = EXT / "raw" / "yt_scrape"
OUT = EXT / "youtube_views.parquet"
OUT_MD = ROOT / "docs" / "numbers_youtube_views.md"
_log = []


def build():
    v = pd.read_parquet(SCRAPE / "videos.parquet")
    v = v[v.status == "OK"]
    hits = pd.read_sql("SELECT video_id, sort FROM hits", sqlite3.connect(SCRAPE / "yt.sqlite"))
    by_views = v.video_id.isin(hits.loc[hits["sort"] == "views", "video_id"])
    out = v.assign(by_views=by_views)[["published_at", "view_count", "age_days", "views_per_day", "br", "br_core", "game", "duration_s", "by_views"]]
    out = out.assign(published_at=out.published_at.dt.tz_localize(None).dt.floor("D")).reset_index(drop=True)
    return out


def show(title, df):
    text = df.to_string()
    print(f"\n== {title}\n{text}")
    _log.append(f"### {title}\n\n```\n{text}\n```\n")


def numbers(v):
    b = v[v.br & ~v.game].assign(year=lambda x: x.published_at.dt.year)
    show("videos in the sample (pages with data)", pd.DataFrame({"videos": [len(v)], "brainrot_title": [int(v.br.sum())], "game_in_title": [int(v.game.sum())],
                                                                  "brainrot_excl_game": [len(b)], "found_by_views_sort": [int(b.by_views.sum())]}))
    show("brainrot videos (no game) left out of the chart: published before 2019, under 1 day old (no per-day rate)",
         pd.DataFrame({"before_2019": [int((b.year < 2019).sum())], "under_1_day": [int(b.views_per_day.isna().sum())]}))
    q = lambda p: (lambda x: x.quantile(p))
    g = b[b.year >= 2019].groupby("year").agg(n=("view_count", "size"), median_views=("view_count", "median"), median_views_per_day=("views_per_day", "median"),
                                              p10_per_day=("views_per_day", q(.1)), p90_per_day=("views_per_day", q(.9)))
    show("brainrot videos (no game) by publish year", g.round(0))
    s = b[(b.year >= 2019) & b.by_views].groupby("year").agg(n=("view_count", "size"), median_views=("view_count", "median"), median_views_per_day=("views_per_day", "median"))
    show("same, only videos the views-sorted search found", s.round(0))
    c = b[b.year >= 2019].groupby("year").agg(share_found_by_views_sort=("by_views", "mean"))
    show("share of each year's videos found by the views-sorted search", c.round(2))
    d = b[b.year >= 2019]
    tot = d.view_count.sum()
    sh = d.groupby("year").agg(videos=("view_count", "size"), views=("view_count", "sum"))
    sh = pd.DataFrame({"videos": sh.videos, "share_of_videos_%": 100 * sh.videos / sh.videos.sum(), "share_of_views_%": 100 * sh.views / tot})
    show("brainrot videos (no game) from 2019: share of videos found and of all views by publish year", sh.round(1))
    show("views concentration, same videos", pd.DataFrame({"videos": [len(d)], "total_views": [int(tot)], "top10_share_%": [round(100 * d.view_count.nlargest(10).sum() / tot, 1)],
                                                         "top1pct_share_%": [round(100 * d.view_count.nlargest(len(d) // 100).sum() / tot, 1)]}))
    return b


def reddit_link(b):
    # youtube brainrot videos by publish month vs reddit brainrot rate (comments, core + extended tiers), 2022-06..2026-09
    lm = pd.read_parquet(AGG / "lexicon_monthly.parquet")
    lm = lm[(lm.type == "comment") & lm.tier.isin(["core", "extended"])]

    def rate(subs):
        d = lm[lm.subreddit.isin(subs)].groupby("month")[["hits", "tokens"]].sum()
        return d.hits / d.tokens * 1e4

    red = {"all six": rate(["memes", "teenagers", "books", "explainlikeimfive", "todayilearned", "nosurf"]), "memes + teenagers": rate(["memes", "teenagers"])}
    d = b.assign(month=b.published_at.dt.to_period("M").dt.to_timestamp()).groupby("month").agg(videos=("view_count", "size"), views=("view_count", "sum"))
    months = pd.date_range("2022-06-01", "2026-09-01", freq="MS")

    def r_p(a, c):  # null: circular shifts of one series (keeps its autocorrelation), at least 6 months
        a, c = np.asarray(a, float), np.asarray(c, float)
        r = spearmanr(a, c).correlation
        null = [spearmanr(np.roll(a, k), c).correlation for k in range(6, len(a) - 5)]
        return r, float(np.mean(np.abs(null) >= abs(r)))

    rows = []
    for rn, rs in red.items():
        R = rs.reindex(months)
        for yn in ("videos", "views"):
            Y = d[yn].reindex(months).fillna(0)
            r, p = r_p(Y, R)
            dr, dp = r_p(Y.diff().dropna(), R.diff().dropna())
            lag = {k: spearmanr(Y.shift(k).iloc[3:-3], R.iloc[3:-3]).correlation for k in (-3, 0, 3)}
            rows.append({"reddit": rn, "youtube": yn, "r_levels": r, "p_levels": p, "r_changes": dr, "p_changes": dp,
                         "r_yt_3m_before": lag[3], "r_yt_3m_after": lag[-3]})
    show(f"youtube brainrot videos (no game) by publish month vs reddit brainrot rate, {len(months)} months 2022-06..2026-09 (Spearman; p from circular shifts)",
         pd.DataFrame(rows).set_index(["reddit", "youtube"]).round(2))
    show("top months: reddit rate (memes + teenagers, per 10,000 words), youtube views (millions), youtube videos found",
         pd.DataFrame({"reddit_top5": [", ".join(f"{m:%Y-%m} {x:.2f}" for m, x in red["memes + teenagers"].reindex(months).nlargest(5).items())],
                       "youtube_views_top5": [", ".join(f"{m:%Y-%m} {x / 1e6:.0f}" for m, x in d.views.reindex(months).nlargest(5).items())],
                       "youtube_videos_top5": [", ".join(f"{m:%Y-%m} {x:.0f}" for m, x in d.videos.reindex(months).nlargest(5).items())]}).T)


def main():
    v = build()
    v.to_parquet(OUT, index=False)
    print(f"wrote {OUT} ({len(v):,} rows)")
    reddit_link(numbers(v))
    OUT_MD.write_text("# Numbers behind the YouTube views chart\n\nWritten by `python -m src.yt_views` (numeric tables only).\n\n" + "\n".join(_log))
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
