"""Look inside the scraped YouTube dataset (reads yt.sqlite, never touches the network).

    python -m src.yt_peek                     # summary and 15 random rows
    python -m src.yt_peek --n 40 --brainrot   # 40 random brainrot-titled videos
    python -m src.yt_peek --csv               # also write full CSVs you can open in Excel / Numbers / VS Code

CSV files (git-ignored, they contain titles and comment text) go to data/external/raw/yt_scrape/:
    videos_full.csv     one row per video, every parsed field (tags joined with |, description cut at 300 characters)
    comments_full.csv   top comments with the video's title, text only, no authors
videos_live.csv (written by yt_run while it runs) has a shorter column set and is always up to date.
"""
import argparse
import sqlite3

import pandas as pd

from .yt_browser import DB, RAW
from .yt_dataset import build

SHOW = ["published_at", "title", "channel_title", "view_count", "like_count", "comment_count", "duration_s", "views_per_day", "br", "found_by"]


def export(v, con):
    """Full CSVs next to the database (utf-8 with BOM so Excel shows emoji and non-Latin titles correctly)."""
    out = v.drop(columns=["related"]).assign(tags=v.tags.map("|".join), caption_langs=v.caption_langs.map("|".join), found_by=v.found_by.map(lambda x: "|".join(x) if isinstance(x, list) else x),
                                             description=v.description.str.slice(0, 300))
    out["published_at"], out["fetched_at"] = out.published_at.dt.strftime("%Y-%m-%d %H:%M"), out.fetched_at.dt.strftime("%Y-%m-%d %H:%M")
    out.to_csv(RAW / "videos_full.csv", index=False, encoding="utf-8-sig")
    c = pd.read_sql("SELECT video_id, rank, text, likes_text FROM comments", con).merge(v[["video_id", "title"]], on="video_id", how="left")
    c[["video_id", "title", "rank", "text", "likes_text"]].to_csv(RAW / "comments_full.csv", index=False, encoding="utf-8-sig")
    print(f"wrote {RAW / 'videos_full.csv'} ({len(out):,} rows, {out.shape[1]} columns) and {RAW / 'comments_full.csv'} ({len(c):,} comments)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=15, help="rows to show")
    ap.add_argument("--brainrot", action="store_true", help="only videos whose title matches the brainrot lexicon")
    ap.add_argument("--csv", action="store_true", help="write videos_full.csv and comments_full.csv")
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    v = build(con)
    ok = v[v.status == "OK"]
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_colwidth", 55)
    print(f"{len(v):,} pages fetched: {v.status.value_counts().to_dict()}")
    print(f"found by search but not fetched yet: {pd.read_sql('SELECT count(DISTINCT video_id) AS n FROM hits', con).n[0] - len(v):,}")
    print(f"brainrot-titled: {int(ok.br.sum()):,} of {len(ok):,} ok pages ({100 * ok.br.mean():.0f}%); comments stored: {pd.read_sql('SELECT count(*) AS n FROM comments', con).n[0]:,}")
    yr = ok.groupby(ok.published_at.dt.year).agg(videos=("video_id", "size"), brainrot=("br", "sum"), median_views=("view_count", "median"))
    print("\nby publish year:\n" + yr.to_string())
    print("\nmissing values among ok pages (%):\n" + (100 * ok[["like_count", "comment_count", "subscribers_approx", "duration_s"]].isna().mean()).round(1).to_string())
    rows = (ok[ok.br] if a.brainrot else ok)
    print(f"\n{min(a.n, len(rows))} random {'brainrot-titled ' if a.brainrot else ''}rows:")
    print(rows.sample(min(a.n, len(rows)), random_state=None)[SHOW].to_string(index=False))
    if a.csv:
        export(v, con)
    else:
        print("\n(add --csv to write full CSV files)")


if __name__ == "__main__":
    main()
