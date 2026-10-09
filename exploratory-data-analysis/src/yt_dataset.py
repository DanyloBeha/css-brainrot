"""Video-level dataset from the scraped YouTube pages (reads data/external/raw/yt_scrape/yt.sqlite, filled by `src.yt_browser`).

Run `python -m src.yt_dataset` to rebuild:
    data/external/raw/yt_scrape/videos.parquet    one row per video, with title, description, tags (row-level text: LOCAL, git-ignored)
    data/external/raw/yt_scrape/comments.parquet  comments, text only, no authors, with the age as YouTube writes it and the posting
                                                  period that age allows (LOCAL, git-ignored)
    data/external/youtube_scrape_monthly.parquet  per publish month, numbers only (tracked)
    docs/numbers_youtube_scrape.md                numeric tables behind everything quoted from this dataset

The videos are what the search pages showed for the lexicon queries, a ranked sample and not a census: counts of videos found are NOT
rates. View, like and comment counts are as of `fetched_at` (not historical): compare `views_per_day`, not `view_count`, across ages.
Numbers keep the page's own precision: `view_count`, `like_count`, `comment_count` exact where the page shows them (null where hidden or
off, never 0), `subscribers_approx` is rounded by YouTube (3 digits). A video is brainrot-titled when its lower-cased title (URLs removed,
curly apostrophes straightened, as for Reddit) matches `lexicons.BRAINROT_RE`; `game` marks "Steal a Brainrot" (`external.GAME_RE`).
"""
import json
import re
import sqlite3
import zlib

import pandas as pd

from .config import EXT, ROOT
from .external import GAME_RE
from .lexicons import BRAINROT_CORE_RE, BRAINROT_EXT_RE, BRAINROT_RE, CURLY, SIGMA_RE, URL_RE
from .yt_browser import DB, RAW

OUT = RAW / "videos.parquet"
OUT_COMMENTS = RAW / "comments.parquet"
OUT_MONTHLY = EXT / "youtube_scrape_monthly.parquet"
OUT_MD = ROOT / "docs" / "numbers_youtube_scrape.md"
_log = []
UNIT = {"": 1, "k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}


def plain(rx):
    """Same pattern with non-capturing groups (pandas warns about capture groups in str.contains)."""
    return re.sub(r"\((?!\?)", "(?:", rx)


def clean(text):
    """Lower case, straight apostrophes, URLs removed (same as `lexicons.clean_sql`)."""
    return re.sub(URL_RE, " ", re.sub(f"[{CURLY}]", "'", text.lower() if isinstance(text, str) else ""))


def number(text):
    """'17,253 Comments' -> 17253, '1.97 million subscribers' -> 1970000, '12K' -> 12000; None when there is no number."""
    m = re.search(r"([\d,]*\.?\d+)\s*(thousand|million|billion|[kmb])?\b", text if isinstance(text, str) else "", flags=re.I)
    return round(float(m.group(1).replace(",", "")) * UNIT[(m.group(2) or "").lower()]) if m else None


AGE_DAYS = {"second": 1 / 86400, "minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30.44, "year": 365.25}


def age_range(age_text, fetched):
    """Posting period allowed by an age as YouTube writes it: "3 years ago" (rounded down) means 3 to 4 years before `fetched`, "5 months ago"
    5 to 6 months, "just now" the last minute. Returns (earliest, latest) timestamps or (NaT, NaT). A comment is never dated more exactly
    than this: older comments are only known to the year, so crisis windows shorter than a year cannot be told apart for them."""
    m = re.match(r"\s*(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", age_text or "")
    if not m:
        return (pd.Timestamp("NaT"), pd.Timestamp("NaT")) if "just now" not in (age_text or "") else (fetched - pd.Timedelta(minutes=1), fetched)
    n, d = int(m.group(1)), AGE_DAYS[m.group(2)]
    return fetched - pd.Timedelta(days=(n + 1) * d), fetched - pd.Timedelta(days=n * d)


def load_comments(con):
    """All stored comments (sort top / newest) with numbers parsed and `posted_from` / `posted_to` / `posted_year` from the age text.
    `posted_year` is the year of the middle of the allowed period; `year_certain` says the whole period lies in that year."""
    c = pd.read_sql("SELECT * FROM comments2", con)
    c["fetched_at"] = pd.to_datetime(c["fetched_at"], utc=True)
    c["age_text"], c["replies_text"] = c.age_text.fillna(""), c.replies_text.fillna("")
    c["likes"], c["replies"] = c.likes_text.map(number), c.replies_text.map(number)
    c["likes"] = c.likes.fillna(0).where(c.age_text != "", None)            # the page shows no number for 0 likes; rows from before the age text was read stay unknown
    rng = [age_range(a, f) for a, f in zip(c.age_text, c.fetched_at)]
    c["posted_from"], c["posted_to"] = [r[0] for r in rng], [r[1] for r in rng]
    mid = c.posted_from + (c.posted_to - c.posted_from) / 2
    c["posted_year"] = mid.dt.year.astype("Int64")
    c["year_certain"] = c.posted_from.dt.year == c.posted_to.dt.year
    return c


def _row(vid, status, raw, fetched):
    r = json.loads(zlib.decompress(raw)) if raw else {}
    d, m = r.get("details", {}), r.get("micro", {})
    off = "turned off" in (r.get("comment_count_text") or "")
    return dict(video_id=vid, fetched_at=fetched, status=status, playability=r.get("playability"), title=d.get("title"), description=d.get("shortDescription"),
                tags=d.get("keywords") or [], channel_id=d.get("channelId"), channel_title=d.get("author"), category=m.get("category"),
                published_at=m.get("publishDate"), duration_s=number(d.get("lengthSeconds")), view_count=number(d.get("viewCount")),
                like_count=number(m.get("likeCount")) if m.get("likeCount") else number(r.get("like_text")),
                comment_count=None if off else number(r.get("comment_count_text")), comments_off=off if r.get("comment_count_text") else None,
                subscribers_approx=number(r.get("subscribers_text")), is_live=d.get("isLiveContent"), is_shorts_eligible=m.get("isShortsEligible"),
                family_safe=m.get("isFamilySafe"), countries_available=m.get("availableCountries"), caption_langs=r.get("caption_langs") or [],
                has_auto_captions=any(r.get("auto_captions") or []), related=r.get("related") or [])


def build(con=None):
    """One row per fetched video: parsed page fields, title flags, ages and rates, and how it was found."""
    con = con or sqlite3.connect(DB)
    v = pd.DataFrame([_row(*r) for r in con.execute("SELECT video_id, status, raw, fetched_at FROM videos")])
    h = pd.read_sql("SELECT video_id, term, sort, rank, source, views_text FROM hits", con)
    f = h.groupby("video_id").agg(found_by=("term", lambda x: sorted(set(x))), n_queries=("term", "nunique"), best_rank=("rank", "min"),
                                  list_source=("source", "first"), list_views_text=("views_text", "first"))
    v = v.merge(f, left_on="video_id", right_index=True, how="left")
    v["published_at"] = pd.to_datetime(v["published_at"], utc=True, errors="coerce")
    v["fetched_at"] = pd.to_datetime(v["fetched_at"], utc=True)
    v["age_days"] = (v["fetched_at"] - v["published_at"]).dt.total_seconds() / 86400
    v["views_per_day"] = v["view_count"] / v["age_days"].where(v["age_days"] >= 1)
    v["likes_per_view"] = v["like_count"] / v["view_count"].where(v["view_count"] > 0)
    v["comments_per_view"] = v["comment_count"] / v["view_count"].where(v["view_count"] > 0)
    t, d = v["title"].map(clean), v["description"].map(clean)
    v["br"] = t.str.contains(plain(BRAINROT_RE), regex=True)
    v["matched"] = t.str.extract("(" + plain(BRAINROT_RE) + ")", expand=False).str.replace(r"[ -]", "", regex=True)       # the word that made it brainrot-titled
    v["br_core"], v["br_ext"] = t.str.contains(plain(BRAINROT_CORE_RE), regex=True), t.str.contains(plain(BRAINROT_EXT_RE), regex=True)
    v["sigma"], v["game"] = t.str.contains(plain(SIGMA_RE), regex=True), t.str.contains(GAME_RE, regex=True)
    v["br_desc"] = d.str.contains(plain(BRAINROT_RE), regex=True)
    v["br_tags"] = v["tags"].map(lambda x: bool(re.search(BRAINROT_RE, clean(" ".join(x)))))
    return v


def monthly(v):
    """Per publish month (numbers only, tracked): videos found, brainrot-titled with and without the game, short-length share, views per day."""
    v = v.dropna(subset=["published_at"]).assign(month=lambda x: x.published_at.dt.tz_localize(None).dt.to_period("M").dt.to_timestamp())
    g = v.groupby("month")
    out = pd.DataFrame({"videos": g.size(), "brainrot_title": g.br.sum(), "brainrot_excl_game": g.apply(lambda x: (x.br & ~x.game).sum(), include_groups=False),
                        "short_len_share": g.apply(lambda x: (x.duration_s <= 60).mean(), include_groups=False),
                        "median_views_per_day": g.views_per_day.median(), "median_views_per_day_brainrot": v[v.br].groupby("month").views_per_day.median()})
    return out.reset_index()


def show(title, df):
    text = df.to_string() if hasattr(df, "to_string") else str(df)
    print(f"\n== {title}\n{text}")
    _log.append(f"### {title}\n\n```\n{text}\n```\n")


def spot_check(v, n=50, seed=42):
    """Row-level (terminal only, never saved): n random brainrot-titled videos, to judge by eye whether the matches are valid."""
    for _, r in v[v.br].sample(min(n, int(v.br.sum())), random_state=seed).iterrows():
        print(f"{r.video_id}  {str(r.published_at)[:10]}  {r.title}")


def numbers(v, con):
    """Numeric tables for docs/numbers_youtube_scrape.md."""
    s = pd.read_sql("SELECT term, sort, results, reached_end, seconds FROM searches ORDER BY fetched_at", con)
    show("search runs: videos shown per query and sort, whether the results ran out (reached_end 1) or the cap was hit", s.set_index(["term", "sort"]))
    show("pages fetched by status and playability", v.groupby(["status", "playability"], dropna=False).size().to_frame("videos"))
    ok = v[v.status == "OK"]
    miss = pd.DataFrame({"missing": ok.isna().sum(), "share_%": 100 * ok.isna().mean()})
    show("fields missing among videos with a playable page (null, never 0: hidden likes, comments off, no tags ...)", miss[miss.missing > 0].round(1))
    y = ok.assign(year=ok.published_at.dt.year).groupby("year").agg(videos=("video_id", "size"), brainrot_title=("br", "sum"), brainrot_excl_game=("br", lambda x: (x & ~ok.loc[x.index, "game"]).sum()),
                                                                    median_views_per_day=("views_per_day", "median"), short_len_share=("duration_s", lambda x: (x <= 60).mean()))
    show("videos found per publish year (a ranked sample, not rates)", y.round(3))
    show("brainrot flag: title vs description vs tags (videos)", pd.DataFrame({"title": [int(ok.br.sum())], "description_only": [int((ok.br_desc & ~ok.br).sum())],
                                                                              "tags_only": [int((ok.br_tags & ~ok.br & ~ok.br_desc).sum())], "game_in_title": [int(ok.game.sum())]}))
    c = ok.channel_id.value_counts()
    show("channels: videos per channel and share of the 10 largest channels", pd.DataFrame({"channels": [len(c)], "videos": [int(c.sum())], "max_per_channel": [int(c.iloc[0])],
                                                                                           "top10_share_%": [round(100 * c.head(10).sum() / c.sum(), 1)]}))
    both = ok.dropna(subset=["view_count"]).assign(list_views=ok.list_views_text.map(number))
    both = both[both.list_views > 0]
    rel = ((both.view_count - both.list_views).abs() / both.list_views)
    show("list-page views vs watch-page views (relative difference; the pages were fetched minutes to days apart)", rel.describe().round(4).to_frame("relative_difference"))
    c = load_comments(con)
    if len(c):
        show("comments stored (text only, no authors) by sort", c.groupby("sort").agg(comments=("rank", "size"), videos=("video_id", "nunique"), with_age=("age_text", lambda x: (x != "").mean()),
                                                                                  median_likes=("likes", "median"), pinned=("pinned", "sum"), hearted=("hearted", "sum")).round(3))
        by = c.dropna(subset=["posted_year"]).groupby(["sort", "posted_year"]).agg(comments=("rank", "size"), year_certain_share=("year_certain", "mean")).round(2)
        show("comments by estimated posting year (age rounded down by YouTube: the year is the middle of the allowed period)", by)


def main():
    con = sqlite3.connect(DB)
    v = build(con)
    v.to_parquet(OUT, index=False)
    load_comments(con).to_parquet(OUT_COMMENTS, index=False)
    monthly(v[v.status == "OK"]).to_parquet(OUT_MONTHLY, index=False)
    print(f"wrote {OUT} ({len(v):,} videos), {OUT_COMMENTS}, {OUT_MONTHLY}")
    numbers(v, con)
    OUT_MD.write_text("# Numbers behind the scraped YouTube dataset\n\nWritten by `python -m src.yt_dataset` (numeric tables only; row-level text stays in `data/external/raw/`).\n\n"
                      + "\n".join(_log))
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
