"""External series. Each loader downloads once into data/external/raw (ignored) and caches a small extract (tracked)."""
import urllib.request

import pandas as pd

from .config import EXT

WUI_URL = "https://worlduncertaintyindex.com/wp-content/uploads/2026/09/WUI_M_dataset_2026_08.xlsx"


def load_wui():
    """World Uncertainty Index, monthly (Ahir, Bloom, Furceri): global GDP-weighted average and the USA series.

    Source page: https://worlduncertaintyindex.com/data/ (monthly dataset, updated 2026-09-06).
    """
    out = EXT / "wui_monthly.parquet"
    if not out.exists():
        raw = EXT / "raw" / WUI_URL.rsplit("/", 1)[1]
        raw.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            urllib.request.urlretrieve(WUI_URL, raw)
        g = pd.read_excel(raw, sheet_name="F1", header=None, skiprows=3, usecols=[0, 1], names=["month", "wui_global"]).dropna()
        t = pd.read_excel(raw, sheet_name="T1", usecols=["date", "USA"]).rename(columns={"date": "month", "USA": "wui_usa"})
        df = g.merge(t, on="month")
        df["month"] = pd.to_datetime(df["month"])
        df.to_parquet(out, index=False)
    return pd.read_parquet(out)


# ------------------------------------------------------------------ YouTube trending (Kaggle, rsrishav)
YT_DATASET = "rsrishav/youtube-trending-video-dataset"


def download_youtube_trending(countries=("US",)):
    """Download single country files with kagglehub (no Kaggle token was needed on 2026-10-04).

    Kaggle's "download everything" archive of this dataset is broken ("Data not available. This dataset may need its archive
    recreated"), but the per-file API download works. Files go to the kagglehub cache (outside the repo). US file: 156 MB.
    """
    import kagglehub
    return {c: kagglehub.dataset_download(YT_DATASET, path=f"{c}_youtube_trending_data.csv") for c in countries}


def trending_videos(country="US"):
    """One row per video (its highest view count), publish month, and whether title+tags match the brainrot lexicon."""
    import re

    from .lexicons import BRAINROT_RE
    path = download_youtube_trending((country,))[country]
    df = pd.read_csv(path, encoding_errors="replace")
    df["published"] = pd.to_datetime(df["publishedAt"], utc=True).dt.tz_localize(None)
    df["trending"] = pd.to_datetime(df["trending_date"], utc=True).dt.tz_localize(None)
    first, last = df["trending"].min(), df["trending"].max()
    v = df.sort_values("view_count").drop_duplicates("video_id", keep="last").copy()
    text = (v["title"].fillna("") + " " + v["tags"].fillna("")).str.lower()
    rx = re.compile(re.sub(r"\((?!\?)", "(?:", BRAINROT_RE))        # non-capturing groups: str.contains warns otherwise
    v["brainrot"] = text.str.contains(rx)
    v["game"] = text.str.contains(GAME_RE, regex=True)
    v["month"] = v["published"].dt.to_period("M").dt.to_timestamp()
    v.attrs.update(country=country, rows=len(df), trending_first=first, trending_last=last)
    return v


GAME_RE = r"steal\s+a\s+brain\s?rot"          # the 2025 Roblox game "Steal a Brainrot": brainrot as a product, not as content style
KESHAV = "keshavbansal95/youtube-trending-videos-dataset"
RS_COUNTRIES = ("US", "GB", "CA", "IN")        # downloaded so far; the other seven files (DE, FR, RU, BR, MX, KR, JP) add about 1.1 GB


def trending_videos_2024_25():
    """Kaggle `keshavbansal95/youtube-trending-videos-dataset` (one 990 MB CSV, about 100 countries, trending dates 2024-10-12 to
    2025-09-26): ONE row per video across all countries (the same video trends in dozens of countries, so counting per country would
    repeat it), with highest view count, publish month, number of countries and the brainrot / game flags. Read with DuckDB."""
    import glob

    import duckdb

    from .lexicons import BRAINROT_RE
    folder, _ = download_capped(KESHAV, None, max_gb=1.0)
    csv = glob.glob(f"{folder}/*.csv")[0]
    con = duckdb.connect()
    text = "lower(coalesce(video_title, '') || ' ' || coalesce(video_tags, ''))"
    df = con.execute(f"""
        SELECT video_id, count(DISTINCT video_trending_country) AS countries, max(try_cast(video_view_count AS BIGINT)) AS view_count,
               min(try_cast(video_published_at AS TIMESTAMP)) AS published, min(try_strptime(video_trending__date, '%Y.%m.%d')) AS trending,
               bool_or(regexp_matches({text}, '{BRAINROT_RE}')) AS brainrot, bool_or(regexp_matches({text}, '{GAME_RE}')) AS game
        FROM read_csv('{csv}', header=true, all_varchar=true, ignore_errors=true)
        GROUP BY video_id""").df()
    df["published"] = pd.to_datetime(df["published"]).dt.tz_localize(None)
    df["month"] = df["published"].dt.to_period("M").dt.to_timestamp()
    return df


def _monthly(v, source):
    g = v.groupby("month").agg(videos=("video_id", "size"), brainrot_videos=("brainrot", "sum"))
    g["brainrot_excl_game"] = v[v.brainrot & ~v.game].groupby("month").size().reindex(g.index).fillna(0).astype(int)
    h = v[v.brainrot].groupby("month")["view_count"].agg(median_views="median", mean_views="mean")
    return g.join(h).reset_index().assign(source=source)


def trending_monthly(countries=RS_COUNTRIES):
    """Per source and publish month: unique videos on the trending lists, brainrot-titled videos (with and without the Roblox game),
    median and mean views of the brainrot videos. rsrishav = the given countries together (Aug 2020 - Apr 2024, up to 200 videos a day
    per country); keshavbansal95 = about 100 countries together (trending 2024-10-12 to 2025-09-26). The two lists are built
    differently and there is a gap from mid-April to mid-October 2024: compare shares within a source, never counts across sources."""
    rs = pd.concat([trending_videos(c) for c in countries]).sort_values("view_count").drop_duplicates("video_id", keep="last")
    out = pd.concat([_monthly(rs, "rsrishav"), _monthly(trending_videos_2024_25(), "keshavbansal95")], ignore_index=True)
    out.to_parquet(EXT / "youtube_trending_monthly.parquet", index=False)
    return out


def download_capped(handle, path=None, max_gb=1.0, probe_seconds=6):
    """kagglehub download that aborts when the announced size is above `max_gb` (the plan asks before anything over ~1 GB).

    Returns (local_path_or_None, size_in_bytes_or_None). Run as a subprocess so the progress bar can be read.
    """
    import os
    import re
    import subprocess
    import sys
    import time
    code = f"import kagglehub; print(kagglehub.dataset_download({handle!r}" + (f", path={path!r}" if path else "") + "))"
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    time.sleep(probe_seconds)
    os.set_blocking(p.stderr.fileno(), False)
    try:
        err = p.stderr.read() or ""
    except Exception:
        err = ""
    sizes = re.findall(r"/\s*([\d.]+)([kMG]?)B?\s*\[", err)
    scale = {"": 1, "k": 1e3, "M": 1e6, "G": 1e9}
    size = float(sizes[-1][0]) * scale[sizes[-1][1]] if sizes else None
    if size and size > max_gb * 1e9:
        p.terminate()
        return None, size
    out, _ = p.communicate(timeout=1800)
    return out.strip().splitlines()[-1] if out.strip() else None, size
