"""Daily popularity of YouTube trending videos, overall and for brainrot-titled videos.

Run `python -m src.trending` to rebuild data/external/youtube_trending_daily.parquet and docs/numbers_trending.md.

Sources (read from the kagglehub cache through `external`; they are built differently, compare shares within a source only):
    rsrishav         US, GB, CA, IN (`external.RS_COUNTRIES`), trending dates 2020-08-12 to 2024-04-15, up to 200 videos a day per country
    keshavbansal95   110 countries, trending dates 2024-10-12 to 2025-09-26
Between the two there is a gap (2024-04-16 to 2024-10-11). Its days are rows with status "gap" and empty values, never zeros.

One row per source, country and trending day (`day`). `country` is "ALL" for the pooled series of a source.
    status          data = the list was seen that day; no_list = between a country's first and last list, but no list that day
                    (values empty); gap = day between the two sources (only on the pooled rows, source empty, values empty)
    n_videos        unique videos on the list that day
    views_snapshot  sum of the cumulative view count of those videos on that day: a popularity LEVEL, not views gained that day
    views_new       sum over videos of (view count today - view count yesterday), only where the same video was on the list of the
                    same country on the previous calendar day too. A video's first day is not counted, nor its first day after an
                    absence. Negative differences (the source's view count fell) stay in the sum and are counted in the numbers file.
    n_new           how many videos views_new is summed over (it is a sum over fewer videos than n_videos, and a lower bound of daily views)
    n_negative      how many videos had a negative change that day (a view count cannot fall: a source error, kept in views_new)
    max_new, min_new  the largest and the smallest single-video change that day (shows days that one video carries)
The same four columns (not n_negative) exist for brainrot-titled videos: prefix `br_` (title matches `lexicons.BRAINROT_RE`, the Roblox game included)
and `brx_` (the same without the game "Steal a Brainrot", `external.GAME_RE`). Shares: `br_share_videos`, `br_share_snapshot`,
`br_share_new` (brainrot / all) and the same with `brx_`. A day with a list but no brainrot video has 0 videos and 0 views (a real zero).

Pooled series ("ALL"): a video counts ONCE per day, with its highest view count across the source's countries (the same video trends in
dozens of countries, so summing countries would count it again and again). views_new of the pooled series is the day-over-day change of
that per-video maximum. Pooled rsrishav = 4 countries, pooled keshavbansal95 = 110: levels are not comparable between the sources.

A video is brainrot-titled when its lower-cased title (URLs removed, as for the Reddit text) matches the brainrot lexicon. Tags are not used:
a tag is a hidden search keyword and says nothing about what the viewer sees (`tag_only_check` counts what tags would add).
"""
import glob

import duckdb
import pandas as pd

from .config import EXT, ROOT
from .external import GAME_RE, KESHAV, RS_COUNTRIES, download_capped, download_youtube_trending
from .lexicons import BRAINROT_RE, clean_sql

OUT = EXT / "youtube_trending_daily.parquet"
# DuckDB's default dialect guess drops rows with quoted line breaks (US file: 56,521 of 268,787 rows); these options read them all
CSV = "header=true, all_varchar=true, ignore_errors=true, strict_mode=false, parallel=false, quote='\"', escape='\"'"
OUT_MD = ROOT / "docs" / "numbers_trending.md"
GROUPS = {"": "TRUE", "br_": "br", "brx_": "br AND NOT game"}        # column prefix -> SQL filter on the video-day flags
_log = []


def _con():
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con


def load_rows(con):
    """Table `rows` in `con`: one row per list entry of both sources: source, country, video_id, day, views, br (title matches the
    brainrot lexicon), game (title matches the Roblox game), br_tag (title or tags match). Entries without a date or a view count stay
    in the table (null) so that they can be counted."""
    paths = download_youtube_trending(RS_COUNTRIES)
    folder, size = download_capped(KESHAV, None, max_gb=1.0)
    if folder is None:
        raise RuntimeError(f"{KESHAV} is {size / 1e9:.2f} GB, above the 1 GB limit: ask Ivan before downloading")
    ks = glob.glob(f"{folder}/*.csv")[0]
    title, tags = clean_sql("coalesce({t}, '')"), clean_sql("coalesce({t}, '') || ' ' || coalesce({g}, '')")
    parts = []
    for c in RS_COUNTRIES:
        parts.append(f"""SELECT 'rsrishav' AS source, '{c}' AS country, video_id, try_cast(left(trending_date, 10) AS DATE) AS day,
                                try_cast(try_cast(view_count AS DOUBLE) AS BIGINT) AS views, {title.format(t='title')} AS ttl,
                                {tags.format(t='title', g='tags')} AS ttl_tags
                         FROM read_csv('{paths[c]}', {CSV})""")
    parts.append(f"""SELECT 'keshavbansal95', video_trending_country, video_id, try_strptime(video_trending__date, '%Y.%m.%d')::DATE,
                           try_cast(try_cast(video_view_count AS DOUBLE) AS BIGINT), {title.format(t='video_title')},
                           {tags.format(t='video_title', g='video_tags')}
                    FROM read_csv('{ks}', {CSV})""")
    con.execute(f"""CREATE TABLE rows AS
        SELECT source, country, video_id, day, views, regexp_matches(ttl, '{BRAINROT_RE}') AS br, regexp_matches(ttl, '{GAME_RE}') AS game,
               regexp_matches(ttl_tags, '{BRAINROT_RE}') AS br_tag
        FROM ({' UNION ALL '.join(parts)})""")


def rows_check(con):
    """Rows loaded per file next to an independent count (pandas, one column, in chunks); they must be equal."""
    paths = download_youtube_trending(RS_COUNTRIES)
    paths["keshavbansal95"] = glob.glob(f"{download_capped(KESHAV, None, max_gb=1.0)[0]}/*.csv")[0]
    got = con.execute("SELECT CASE WHEN source = 'rsrishav' THEN country ELSE source END AS file, count(*) AS rows_loaded FROM rows GROUP BY ALL").df().set_index("file")
    got["rows_pandas"] = [sum(len(ch) for ch in pd.read_csv(paths[f], usecols=[0], chunksize=500_000, encoding_errors="replace")) for f in got.index]
    return got.sort_index()


def _video_days(con, pooled):
    """Table `vd_pooled` or `vd_country`: one row per (source[, country], video, day) with its view count, the title flags, and `new` (the
    gain since the previous calendar day, null when the video was not on the list that day). Duplicate list entries of one video on one day
    keep the highest view count. Pooled = a video counts once per day, with its highest view count across the source's countries."""
    keys, name = ("source", "vd_pooled") if pooled else ("source, country", "vd_country")
    con.execute(f"""CREATE OR REPLACE TABLE {name} AS
        WITH d AS (SELECT {keys}, video_id, day, max(views) AS views, bool_or(br) AS br, bool_or(game) AS game, count(*) AS entries
                   FROM rows WHERE day IS NOT NULL AND views IS NOT NULL GROUP BY {keys}, video_id, day),
        v AS (SELECT *, lag(views) OVER w AS pviews, lag(day) OVER w AS pday FROM d WINDOW w AS (PARTITION BY {keys}, video_id ORDER BY day))
        SELECT *, CASE WHEN day - pday = 1 THEN views - pviews END AS new FROM v""")
    return name


def _daily(con, pooled):
    """Aggregate a video-day table to one row per (source, country, day); country = 'ALL' for the pooled table."""
    name = _video_days(con, pooled)
    country = "'ALL'" if pooled else "country"
    cols = []
    for p, f in GROUPS.items():
        cols.append(f"""count(*) FILTER (WHERE {f}) AS {p}n_videos, coalesce(sum(views) FILTER (WHERE {f}), 0) AS {p}views_snapshot,
                        coalesce(sum(new) FILTER (WHERE {f}), 0) AS {p}views_new, count(new) FILTER (WHERE {f}) AS {p}n_new""")
    cols.append("count(*) FILTER (WHERE new < 0) AS n_negative, max(new) AS max_new, min(new) AS min_new")
    return con.execute(f"SELECT source, {country} AS country, day, {', '.join(cols)} FROM {name} GROUP BY ALL ORDER BY ALL").df()


def build(con=None):
    """Daily table (see module docstring): both sources, per country and pooled, with status, shares and the gap rows."""
    con = con or _con()
    if not con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'rows'").fetchone()[0]:
        load_rows(con)
    df = pd.concat([_daily(con, pooled=False), _daily(con, pooled=True)], ignore_index=True)
    df["day"] = pd.to_datetime(df["day"])
    df["status"] = "data"
    for p in GROUPS:
        df[f"{p}views_new"] = df[f"{p}views_new"].where(df["n_new"] > 0)       # no video with a previous day (first day of a list): unknown, not 0
    for p in ("br_", "brx_"):
        df[f"{p}share_videos"] = df[f"{p}n_videos"] / df["n_videos"]
        df[f"{p}share_snapshot"] = df[f"{p}views_snapshot"] / df["views_snapshot"]
        df[f"{p}share_new"] = df[f"{p}views_new"] / df["views_new"]
    # days between a country's first and last list on which it has no list: empty, not zero
    span = df.groupby(["source", "country"])["day"].agg(["min", "max"])
    full = pd.concat([pd.DataFrame({"source": s, "country": c, "day": pd.date_range(r["min"], r["max"])}) for (s, c), r in span.iterrows()])
    df = full.merge(df, on=["source", "country", "day"], how="left")
    df["status"] = df["status"].fillna("no_list")
    # the gap between the two sources: pooled rows only, no source
    ends = df[df.country == "ALL"].groupby("source")["day"].agg(["min", "max"]).sort_values("min")
    gap = pd.DataFrame({"source": None, "country": "ALL", "day": pd.date_range(ends["max"].iloc[0] + pd.Timedelta(days=1), ends["min"].iloc[1] - pd.Timedelta(days=1)),
                        "status": "gap"})
    df = pd.concat([df, gap], ignore_index=True).sort_values(["source", "country", "day"], na_position="first", ignore_index=True)
    counts = [c for c in df.columns if c.endswith(("n_videos", "views_snapshot", "views_new", "n_new", "n_negative", "max_new", "min_new"))]
    df[counts] = df[counts].astype("Int64")
    first = ["source", "country", "day", "status"]
    return df[first + [c for c in df.columns if c not in first]]


def tag_only_check(con):
    """Unique brainrot videos by title, by title or tags, and how many only the tags add (counted for the numbers file)."""
    return con.execute("""
        SELECT source, count(DISTINCT video_id) FILTER (WHERE br) AS by_title, count(DISTINCT video_id) FILTER (WHERE br_tag) AS by_title_or_tags,
               count(DISTINCT video_id) FILTER (WHERE br_tag AND NOT br) AS tags_only
        FROM rows GROUP BY source ORDER BY source""").df().set_index("source")


def us_check(df):
    """Rebuild the US columns with pandas (one file, different code path) and compare with the table: number of days compared and the
    largest absolute difference per column. All differences must be 0."""
    import re
    path = download_youtube_trending(("US",))["US"]
    v = pd.read_csv(path, usecols=["video_id", "title", "trending_date", "view_count"], encoding_errors="replace")
    v["day"] = pd.to_datetime(v["trending_date"].str[:10])
    rx = re.compile(re.sub(r"\((?!\?)", "(?:", BRAINROT_RE))
    v["br"] = v["title"].fillna("").str.lower().str.replace(r"https?://\S+|www\.\S+", " ", regex=True).str.contains(rx)
    v = v.groupby(["video_id", "day"], as_index=False).agg(views=("view_count", "max"), br=("br", "max")).sort_values(["video_id", "day"])
    g = v.groupby("video_id")
    v["new"] = (v["views"] - g["views"].shift()).where((v["day"] - g["day"].shift()).dt.days == 1)
    d = pd.DataFrame({"n_videos": v.groupby("day").size(), "views_snapshot": v.groupby("day")["views"].sum(), "views_new": v.groupby("day")["new"].sum(min_count=1),
                      "br_n_videos": v[v.br].groupby("day").size().reindex(v.day.unique()).fillna(0)})
    t = df[(df.country == "US") & (df.status == "data")].set_index("day")[list(d.columns)].astype(float)
    diff = (t - d.reindex(t.index)).abs()
    return pd.DataFrame({"days_compared": len(t), "max_abs_difference": diff.max()}).T


def show(title, df):
    """Print a table and keep it for docs/numbers_trending.md."""
    text = df.to_string() if hasattr(df, "to_string") else str(df)
    print(f"\n== {title}\n{text}")
    _log.append(f"### {title}\n\n```\n{text}\n```\n")


def coverage(con, df):
    """Per source: rows, unique videos, countries, first and last trending day, days with a pooled list, days without, the gap."""
    r = con.execute("""SELECT source, count(*) AS rows, count(DISTINCT video_id) AS unique_videos, count(DISTINCT country) AS countries,
                              count(*) FILTER (WHERE day IS NULL) AS no_date, count(*) FILTER (WHERE views IS NULL) AS no_views
                       FROM rows GROUP BY source ORDER BY source""").df().set_index("source")
    a = df[df.country == "ALL"]
    d = a[a.source.notna()].groupby("source").agg(first_day=("day", "min"), last_day=("day", "max"), days_with_list=("status", lambda x: (x == "data").sum()),
                                                  days_no_list=("status", lambda x: (x == "no_list").sum()))
    out = r.join(d)
    gap = a[a.status == "gap"]
    show("sources: rows, unique videos, countries, dates (no_date and no_views rows are left out of the table)", out)
    show("gap between the sources (empty rows, not zeros)", pd.DataFrame({"first_day": [gap.day.min().date()], "last_day": [gap.day.max().date()], "days": [len(gap)]}))


def countries(con, df):
    """Per source and country: list entries, unique videos, days with a list, first and last day, unique brainrot-titled videos."""
    r = con.execute("""SELECT source, country, count(*) AS entries, count(DISTINCT video_id) AS unique_videos, count(DISTINCT video_id) FILTER (WHERE br) AS brainrot_videos,
                              count(DISTINCT video_id) FILTER (WHERE br AND NOT game) AS brainrot_excl_game
                       FROM rows GROUP BY ALL""").df().set_index(["source", "country"])
    d = df[(df.country != "ALL") & (df.status == "data")].groupby(["source", "country"])["day"].agg(days_with_list="count", first_day="min", last_day="max")
    out = r.join(d).sort_values(["source", "unique_videos"], ascending=[True, False])
    out["first_day"], out["last_day"] = out["first_day"].dt.date, out["last_day"].dt.date
    show("unique videos and days with a list, per source and country (entries = rows of the source file)", out)


def per_year(df):
    """Pooled series per source and calendar year: days, mean videos and snapshot per day, views gained (sum of views_new), brainrot parts."""
    a = df[(df.country == "ALL") & (df.status == "data")].copy()
    a["year"] = a.day.dt.year
    g = a.groupby(["source", "year"])
    out = pd.DataFrame({"days": g.size(), "videos_per_day": g.n_videos.mean(), "snapshot_per_day_M": g.views_snapshot.mean() / 1e6,
                        "gained_M": g.views_new.sum() / 1e6, "br_videos_per_day": g.br_n_videos.mean(), "br_snapshot_per_day_M": g.br_views_snapshot.mean() / 1e6,
                        "br_gained_M": g.br_views_new.sum() / 1e6, "brx_gained_M": g.brx_views_new.sum() / 1e6})
    out["br_share_gained_%"] = 100 * out.br_gained_M / out.gained_M
    out["brx_share_gained_%"] = 100 * out.brx_gained_M / out.gained_M
    show("pooled series per year: views gained = sum of views_new over the days (millions); snapshot = mean over days of views_snapshot (millions); "
         "n_new differs from n_videos, so gained is a lower bound", out.round(2))
    n = a.groupby("source").agg(days=("day", "size"), zero_br_days=("br_n_videos", lambda x: (x == 0).sum()), zero_brx_days=("brx_n_videos", lambda x: (x == 0).sum()))
    n["zero_br_%"], n["zero_brx_%"] = 100 * n.zero_br_days / n.days, 100 * n.zero_brx_days / n.days
    show("days with data and days with no brainrot-titled video on the pooled list (br = with the game, brx = without)", n.round(1))
    ev = a.assign(quarter=a.day.dt.to_period("Q")).groupby(["source", "quarter"]).agg(days=("day", "size"), br_zero_days=("br_n_videos", lambda x: (x == 0).sum()),
                                                                                      br_videos=("br_n_videos", "sum"), videos=("n_videos", "sum"), br_gained_M=("br_views_new", lambda x: x.sum() / 1e6))
    ev["br_per_1000_videos"] = 1000 * ev.br_videos / ev.videos
    show("pooled series per quarter: brainrot-titled video-days (a video on the list on 3 days counts 3) per 1,000 list entries", ev[ev.br_videos > 0].round(2))


def peaks(df, top=6):
    """Top days per source of the pooled series: views gained by brainrot-titled videos (with and without the game) and by all videos."""
    a = df[(df.country == "ALL") & (df.status == "data")].dropna(subset=["views_new"])
    for col, name in (("br_views_new", "brainrot-titled, game included"), ("brx_views_new", "brainrot-titled, game excluded"), ("views_new", "all videos")):
        t = a.sort_values(col, ascending=False).groupby("source").head(top).sort_values(["source", col], ascending=[True, False])[["source", "day", "n_videos", "n_new", "n_negative", "br_n_videos", "brx_n_videos", col, "max_new"]].copy()
        t["day"] = t["day"].dt.date
        if col != "views_new":
            t["share_of_all_new"] = (t[col] / a.loc[t.index, "views_new"]).round(4)
        t[col + "_M"], t["max_single_video_M"] = (t.pop(col) / 1e6).round(2), (t.pop("max_new") / 1e6).round(2)
        show(f"peak days by views gained, {name} (millions; pooled series; n_negative > 0 or one video carrying the day = see the largest changes)", t.set_index("source"))


def largest_changes(con, top=6):
    """The largest single-video day-over-day changes (per country): a view count that jumps and falls back is a source error."""
    t = con.execute(f"""SELECT source, country, day, pviews, views, new FROM vd_country WHERE new IS NOT NULL ORDER BY abs(new) DESC LIMIT {top}""").df()
    t["day"] = t["day"].dt.date
    show("largest single-video day-over-day changes in view count (per country; video ids left out)", t.set_index("source"))


def new_views_check(con):
    """Negative day-over-day changes, and list entries that get no views_new (first day of a video, or back after an absence)."""
    rows = []
    for name, label in (("vd_country", "per country"), ("vd_pooled", "pooled")):
        q = con.execute(f"""SELECT source, count(*) AS video_days, count(new) AS with_new, count(*) FILTER (WHERE pday IS NULL) AS first_ever,
                                   count(*) FILTER (WHERE pday IS NOT NULL AND day - pday > 1) AS back_after_absence,
                                   count(*) FILTER (WHERE new < 0) AS negative, coalesce(sum(new) FILTER (WHERE new < 0), 0) AS negative_sum,
                                   coalesce(min(new), 0) AS most_negative, coalesce(sum(new), 0) AS new_sum, count(*) FILTER (WHERE new = 0) AS zero,
                                   sum(entries - 1) AS merged_entries
                            FROM {name} GROUP BY source ORDER BY source""").df()
        q.insert(0, "level", label)
        rows.append(q)
    out = pd.concat(rows).set_index(["level", "source"])
    out["negative_%_of_new"] = 100 * out.negative / out.with_new
    out[["merged_entries", "negative_sum", "most_negative", "new_sum"]] = out[["merged_entries", "negative_sum", "most_negative", "new_sum"]].astype("int64")
    show("views_new: video-days with and without a day-over-day change, negative changes (kept in the sums), merged_entries (same video twice on one day in a list, or in several countries when pooled; highest count kept)", out.round(4))
    d = con.execute("""SELECT source, day, sum(new) AS views_new FROM vd_pooled WHERE new IS NOT NULL GROUP BY ALL HAVING sum(new) < 0 ORDER BY source, day""").df()
    show("pooled days on which views_new is negative", d if len(d) else pd.DataFrame({"days": [0]}))


def build_all():
    """Rebuild the Parquet table and return (con, df)."""
    con = _con()
    load_rows(con)
    df = build(con)
    df.to_parquet(OUT, index=False)
    return con, df


def main():
    con, df = build_all()
    print(f"wrote {OUT} ({len(df):,} rows)")
    show("rows loaded per file next to an independent count (must be equal)", rows_check(con))
    show("US columns rebuilt with pandas vs the table (days where the table is empty are skipped)", us_check(df))
    coverage(con, df)
    countries(con, df)
    per_year(df)
    peaks(df)
    new_views_check(con)
    largest_changes(con)
    show("unique brainrot-titled videos: by title (used here), by title or tags, added by tags only", tag_only_check(con))
    OUT_MD.write_text("# Numbers behind the YouTube trending daily table\n\nWritten by `python -m src.trending` (numeric tables only; row-level text is never saved).\n"
                      f"Table: `data/external/youtube_trending_daily.parquet` ({len(df):,} rows). Definitions are in the docstring of `src/trending.py`.\n\n" + "\n".join(_log))
    print(f"\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()
