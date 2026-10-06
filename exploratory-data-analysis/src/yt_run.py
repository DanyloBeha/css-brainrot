"""One command for the whole YouTube collection: find videos by search, fetch each video's page, save every video as it arrives.

    caffeinate -i python -m src.yt_run                                  # defaults below; caffeinate keeps the Mac awake
    python -m src.yt_run --target 20000 --batch-size 250 --comments 0   # same, other settings
    python -m src.yt_run --workers 5                                    # more browsers at once (max 6)
    python -m src.yt_run --search-only                                  # only find videos (all queries), fetch nothing

Settings (change the constants here or pass the flags):
    BATCH_SIZE   videos fetched per round. After each round the script checks how many found-but-unfetched videos are left and, if there are
                 fewer than one batch, runs more searches first (so a batch is also the unit of "look for new videos").
    TARGET       stop when this many videos have been fetched (counted over all runs, so a second run continues where the first stopped).
    WORKERS      browsers running at the same time (separate processes, about 0.5 GB of memory each). Each keeps its own pause of
                 3 s between its page loads, so the speed is roughly WORKERS times one browser, and so is the load on YouTube: a CAPTCHA
                 stops all of them at once.
    COMMENTS     top comments (text only, no authors) saved per video; 0 = none (faster).

How new videos are found: by SEARCH. Every query in `yt_browser.all_terms` (the lexicon terms, then "<core term> <year>" for 2020-2026) is
run twice, sorted by view count and by upload date, and scrolled to the end (about 450-500 videos per run). Add queries in `QUERIES` in
yt_browser.py. With --snowball, the "related videos" shown next to brainrot-titled videos are added as candidates when the queries run out
(they are checked by title after fetching, so some are not brainrot: they form a context sample and are not the search sample).

Progress: a bar with speed and time left, and the file data/external/raw/yt_scrape/videos_live.csv gets one new line per video right
away (open it any time; git-ignored, it contains titles). Everything is also in yt.sqlite; Ctrl-C is safe and a new run continues.
When done: `python -m src.yt_dataset` builds the full Parquet dataset and docs/numbers_youtube_scrape.md.
"""
import argparse
import csv
import json
import re
import time
import zlib

import pandas as pd
from tqdm import tqdm

from .config import ROOT
from .lexicons import BRAINROT_RE
from .yt_browser import PARSER_VERSION, QUERIES, RAW, Blocked, Pool, all_terms, db, now, pending_queries, store_search, store_video, unfetched
from .yt_dataset import _row, build, clean

BATCH_SIZE = 500
TARGET = 10_000
COMMENTS = 10
WORKERS = 3
MAX_RESULTS = 500                      # one search shows at most about 500 videos
SORTS = ("views", "date")
LIVE = RAW / "videos_live.csv"
REPORT = ROOT / "docs" / "youtube_run_report.md"
COLUMNS = ["fetched_at", "video_id", "status", "published_at", "title", "channel_title", "view_count", "like_count", "comment_count", "duration_s",
           "category", "subscribers_approx", "brainrot_title", "found_by", "url"]


def live_row(con, vid, status, raw, fetched):
    """One line of the live CSV from a stored video (raw = compressed slim JSON)."""
    r = _row(vid, status, raw, fetched)
    first = con.execute("SELECT term FROM hits WHERE video_id = ? ORDER BY rank LIMIT 1", (vid,)).fetchone()
    r.update(brainrot_title=bool(re.search(BRAINROT_RE, clean(r["title"]))), found_by=first[0] if first else None, url=f"https://www.youtube.com/watch?v={vid}")
    return {c: r.get(c) for c in COLUMNS}


def append_live(rows):
    new = not LIVE.exists()
    with LIVE.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS)
        if new:
            w.writeheader()
        w.writerows(rows)


def backfill(con):
    """Videos fetched before the live file existed are written to it once."""
    if LIVE.exists():
        return
    rows = [live_row(con, v, s, raw, f) for v, s, raw, f in con.execute("SELECT video_id, status, raw, fetched_at FROM videos WHERE parser_version = ?", (PARSER_VERSION,))]
    if rows:
        append_live(rows)


def n_fetched(con):
    return con.execute("SELECT count(*) FROM videos WHERE parser_version = ?", (PARSER_VERSION,)).fetchone()[0]


def add_related(con):
    """Related videos of brainrot-titled videos that are not candidates yet become candidates (term '(related)', last in line)."""
    seen = {r[0] for r in con.execute("SELECT video_id FROM hits")}
    new = set()
    for (raw,) in con.execute("SELECT raw FROM videos WHERE parser_version = ? AND status = 'OK'", (PARSER_VERSION,)):
        r = json.loads(zlib.decompress(raw))
        if re.search(BRAINROT_RE, clean(r.get("details", {}).get("title"))):
            new.update(x for x in r.get("related", []) if x and x not in seen)
    con.executemany("INSERT OR IGNORE INTO hits VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [(v, "(related)", "related", 1000, now(), "related", None, None, None, None, None, None) for v in new])
    con.commit()
    return len(new)


# ------------------------------------------------------------------ logging and report
def log_event(con, run_id, kind, key, status, error=None, seconds=None, results=None, note=None):
    """One line per search or page attempt. Error text keeps no URL (they hold video ids); status is the page's playability status
    (OK, LOGIN_REQUIRED, UNPLAYABLE ...), or 'error:<ExceptionName>' when the scraper itself failed, or 'blocked'."""
    err = re.sub(r"https?://\S+", "<url>", error)[:160] if error else None
    con.execute("INSERT INTO log VALUES (?,?,?,?,?,?,?,?,?)", (run_id, now(), kind, key, status, err, round(seconds, 1) if seconds is not None else None, results, note))
    con.commit()


def _tier(term):
    base = re.sub(r" 20\d\d$", "", term)
    tier = next((t for t, ts in QUERIES.items() if base in ts), "related" if term == "(related)" else "other")
    return tier + ("+year" if base != term else "")


def _block(df):
    return "```\n" + (df.to_string() if len(df) else "(none)") + "\n```\n"


def report_md(con, run_id=None):
    """Markdown report (numbers only): runs, fetch results with error rate and error types, field completeness, search quality per query,
    tier and sort. `run_id` marks the current run in the first table; everything else covers all runs."""
    log = pd.read_sql("SELECT * FROM log", con)
    runs = pd.read_sql("SELECT * FROM runs ORDER BY started_at", con)
    d = log[log.kind == "detail"]
    out = ["# YouTube collection: run report\n",
           "Written by `python -m src.yt_run` at the end of every run (`--report` rewrites it without running). Numbers only; no titles. "
           "The attempt log starts with the version that added it: earlier pages are in the status table but not in the attempt tables.\n"]
    # runs
    if len(runs):
        r = runs.set_index("run_id")
        g = d.groupby("run_id")
        r["minutes"] = ((pd.to_datetime(r.ended_at) - pd.to_datetime(r.started_at)).dt.total_seconds() / 60).round(1)
        r["pages"], r["ok"] = g.size(), g.apply(lambda x: (x.status == "OK").sum(), include_groups=False)
        r["unusable"] = g.apply(lambda x: (~x.status.eq("OK") & ~x.status.str.startswith(("error:", "blocked"))).sum(), include_groups=False)
        r["scraper_errors"] = g.apply(lambda x: x.status.str.startswith(("error:", "blocked")).sum(), include_groups=False)
        r = r.fillna({"pages": 0, "ok": 0, "unusable": 0, "scraper_errors": 0})
        r["pages_per_hour"] = (3600 * r.pages / (r.minutes * 60)).where(r.minutes > 0).round(0)
        out += ["## Runs\n", "unusable = YouTube answered but the page has no data (login or age check, unavailable); scraper_errors = the scraper failed (timeout, crash) or was blocked.\n",
                _block(r[["started_at", "minutes", "workers", "batch_size", "comments", "ended_by", "pages", "ok", "unusable", "scraper_errors", "pages_per_hour"]]
                       .rename(index={run_id: f"{run_id} (this run)"}))]
    # fetch results, all videos in the database
    v = pd.read_sql("SELECT status, count(*) AS videos FROM videos WHERE parser_version = ? GROUP BY status", con, params=(PARSER_VERSION,)).set_index("status")
    v["share_%"] = (100 * v.videos / v.videos.sum()).round(1)
    out += ["## Pages fetched (all videos in the database)\n", f"Error rate (pages without data) = {100 * (1 - v.videos.get('OK', 0) / v.videos.sum()):.1f}% of {int(v.videos.sum())} pages.\n", _block(v)]
    if len(d):
        bad = d[d.status != "OK"].groupby("status").agg(pages=("key", "size"), median_seconds=("seconds", "median"), example=("error", "first"))
        bad["share_of_attempts_%"] = (100 * bad.pages / len(d)).round(1)
        out += ["## Error types (logged attempts)\n", f"{len(d)} attempts logged; not ok = {int((d.status != 'OK').sum())} ({100 * (d.status != 'OK').mean():.1f}%); "
                f"scraper errors = {int(d.status.str.startswith(('error:', 'blocked')).sum())} ({100 * d.status.str.startswith(('error:', 'blocked')).mean():.1f}%).\n", _block(bad),
                "Seconds per page (all attempts):\n", _block(d.seconds.describe(percentiles=[.5, .9, .99]).round(1).to_frame("seconds"))]
    # completeness of the ok pages
    vids = build(con)
    ok = vids[vids.status == "OK"]
    miss = pd.DataFrame({"missing": ok[["published_at", "view_count", "like_count", "comment_count", "duration_s", "category", "subscribers_approx"]].isna().sum()})
    miss["share_%"] = (100 * miss.missing / max(len(ok), 1)).round(1)
    miss.loc["tags (none given)"] = [int((ok.tags.map(len) == 0).sum()), round(100 * (ok.tags.map(len) == 0).mean(), 1)]
    miss.loc["comments_off (true)"] = [int(ok.comments_off.fillna(False).sum()), round(100 * ok.comments_off.fillna(False).mean(), 1)]
    out += [f"## Fields of the {len(ok)} ok pages\n", "Missing = null in the dataset (hidden likes, comments off, comment count not read in time), never filled with 0.\n", _block(miss)]
    # search
    s = pd.read_sql("SELECT term, sort, fetched_at, results, reached_end, seconds FROM searches", con)
    h = pd.read_sql("SELECT video_id, term, sort, fetched_at, title FROM hits WHERE term != '(related)'", con)
    if len(s):
        first = h.sort_values("fetched_at").drop_duplicates("video_id")
        s["new_unique"] = first.groupby(["term", "sort"]).size().reindex(pd.MultiIndex.from_frame(s[["term", "sort"]])).fillna(0).astype(int).values
        h["match"] = h.title.map(lambda t: bool(re.search(BRAINROT_RE, clean(t))))
        s["title_match_%"] = (100 * h.groupby(["term", "sort"]).match.mean().reindex(pd.MultiIndex.from_frame(s[["term", "sort"]])).values).round(1)
        s["overlap_%"] = (100 * (1 - s.new_unique / s.results.where(s.results > 0))).round(1)
        s["ended"] = s.apply(lambda r: "cap" if r.results >= MAX_RESULTS and not r.reached_end else ("end" if r.reached_end else "stopped"), axis=1)
        s["tier"] = s.term.map(_tier)
        q = s.sort_values("fetched_at").set_index(["term", "sort"])[["tier", "results", "new_unique", "overlap_%", "title_match_%", "ended", "seconds"]]
        tot = pd.DataFrame({"queries": [len(s)], "videos_shown": [int(s.results.sum())], "unique_videos": [int(h.video_id.nunique())],
                            "duplicate_share_%": [round(100 * (1 - h.video_id.nunique() / max(s.results.sum(), 1)), 1)],
                            "title_match_%_of_unique": [round(100 * first.title.map(lambda t: bool(re.search(BRAINROT_RE, clean(t)))).mean(), 1)],
                            "ended_at_cap": [int((s.ended == "cap").sum())], "ran_out_of_results": [int((s.ended == "end").sum())], "minutes_of_search": [round(s.seconds.sum() / 60, 1)]})
        by = lambda k: s.groupby(k).agg(queries=("term", "size"), shown=("results", "sum"), new_unique=("new_unique", "sum"), **{"title_match_%_avg": ("title_match_%", "mean")},
                                        seconds_per_query=("seconds", "mean")).round(1)
        sl = log[(log.kind == "search") & ~log.status.eq("ok")]
        out += ["## Search quality\n", "shown = videos the query listed; new_unique = not seen in an earlier query; overlap = share already seen; title_match = share of listed videos whose "
                "title matches the brainrot lexicon (the rest matched the query in the description, tags or by YouTube's loose matching); ended: cap = the cap was reached, "
                "end = YouTube had no more results, stopped = scrolling stalled.\n", _block(tot), "By tier:\n", _block(by("tier")), "By sort:\n", _block(by("sort")),
                "Per query:\n", _block(q.round(1)), "Failed searches (logged):\n", _block(sl.groupby("status").agg(searches=("key", "size"), example=("error", "first")))]
    return "\n".join(out)


def write_report(con, run_id=None):
    text = report_md(con, run_id)
    REPORT.write_text(text)
    return text


def run(target=TARGET, batch_size=BATCH_SIZE, comments=COMMENTS, years=True, snowball=False, headed=False, workers=WORKERS, search_only=False, max_queries=None):
    con = db()
    backfill(con)
    run_id = now()
    con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)", (run_id, run_id, None, workers, batch_size, target, comments, None))
    con.commit()
    done, t_start, ok, errors, brainrot, bad_in_row, ended_by = n_fetched(con), time.time(), 0, 0, 0, 0, "target reached"
    queries = pending_queries(con, all_terms(years), SORTS, MAX_RESULTS)[:max_queries]
    found = con.execute("SELECT count(DISTINCT video_id) FROM hits").fetchone()[0]
    print(f"{done} videos fetched so far, target {target}, batch {batch_size}, {workers} browsers; {found} found by search, {len(queries)} searches left; live file: {LIVE}")
    pool = Pool(workers, not headed)
    bar = tqdm(total=target, initial=done, unit="video", dynamic_ncols=True)
    try:
        while done < target:
            todo = unfetched(con)
            while (len(todo) < batch_size or search_only) and queries:                    # look for new videos, `workers` queries at a time
                chunk = [queries.pop(0) for _ in range(min(workers, len(queries)))]
                bar.set_description("searching " + ", ".join(f"{t!r} by {s}" for t, s in chunk))
                for term, sort in chunk:
                    pool.submit(("search", term, sort, MAX_RESULTS))
                for _ in chunk:
                    task, out, err, sec = pool.get()
                    key = f"{task[1]} | {task[2]}"
                    if err and err.startswith("blocked"):
                        log_event(con, run_id, "search", key, "blocked", err, sec)
                        raise Blocked(err)
                    if err:
                        log_event(con, run_id, "search", key, f"error:{err.split(':')[0]}", err, sec)
                        bar.write(f"  search {task[1]!r} by {task[2]} failed ({err}); it will be tried again next run")
                        continue
                    store_search(con, task[1], task[2], out[0], out[1], sec)
                    log_event(con, run_id, "search", key, "ok", None, sec, len(out[0]), "end of results" if out[1] else None)
                    bar.write(f"  search {task[1]!r} by {task[2]}: {len(out[0])} videos shown")
                todo = unfetched(con)
            if search_only:
                ended_by = "searches done (search only)"
                bar.write(f"Searches done: {len(todo)} videos waiting to be fetched.")
                break
            if len(todo) < batch_size and snowball and not queries:
                bar.write(f"  queries done: {add_related(con)} related videos added")
                todo = unfetched(con)
            if not todo:
                ended_by = "no videos left to fetch"
                bar.write("No videos left to fetch: add queries (QUERIES in src/yt_browser.py) or run with --snowball.")
                break
            n = min(batch_size, target - done, len(todo))
            bar.write(f"  batch of {n} videos ({len(todo)} waiting)")
            for vid in todo[:n]:
                pool.submit(("detail", vid, comments))
            for k in range(1, n + 1):
                bar.set_description(f"batch {k}/{n}")
                task, out, err, sec = pool.get()
                if err and err.startswith("blocked"):
                    log_event(con, run_id, "detail", task[1], "blocked", err, sec)
                    raise Blocked(err)
                status, raw, cm = out if not err else (f"error:{err.split(':')[0]}", {}, [])
                bad_in_row = bad_in_row + 1 if err else 0
                store_video(con, task[1], status, raw, cm)
                row = live_row(con, task[1], status, zlib.compress(json.dumps(raw).encode()), now())
                missing = status == "OK" and row["comment_count"] in (None, "") and not row.get("comments_off")
                log_event(con, run_id, "detail", task[1], status, err, sec, len(cm), "comment_count_missing" if missing else None)
                append_live([row])
                done, ok, errors, brainrot = done + 1, ok + (status == "OK"), errors + (status != "OK"), brainrot + bool(row["brainrot_title"])
                bar.update(1)
                bar.set_postfix(ok=ok, not_ok=errors, error_rate=f"{100 * errors / (ok + errors):.1f}%", brainrot_title=brainrot,
                                per_hour=int(3600 * (ok + errors) / (time.time() - t_start)))
                if bad_in_row >= 5:
                    raise RuntimeError(f"5 pages in a row failed (last: {err})")
    except Blocked as e:
        ended_by = "blocked (CAPTCHA or unusual traffic)"
        bar.write(f"STOPPED, YouTube asked for a CAPTCHA or reported unusual traffic ({e}). Saved so far: {done} videos. Wait a few hours before the next run.")
    except KeyboardInterrupt:
        ended_by = "interrupted (Ctrl-C)"
        bar.write(f"Interrupted. Saved: {done} videos; run the same command to continue.")
    except RuntimeError as e:
        ended_by = "5 pages in a row failed"
        bar.write(f"STOPPED: {e}. Run again later.")
    finally:
        bar.close()
        pool.close()
        con.execute("UPDATE runs SET ended_at = ?, ended_by = ? WHERE run_id = ?", (now(), ended_by, run_id))
        con.commit()
    write_report(con, run_id)
    types = pd.read_sql("SELECT status, count(*) AS n FROM log WHERE run_id = ? AND kind = 'detail' AND status != 'OK' GROUP BY status ORDER BY n DESC", con, params=(run_id,))
    print(f"this run ({ended_by}): {ok + errors} pages, {ok} ok, {errors} not ok (error rate {100 * errors / max(ok + errors, 1):.1f}%), {brainrot} brainrot-titled, "
          f"{(time.time() - t_start) / 60:.0f} min")
    print("not-ok types: " + (", ".join(f"{r.status} {r.n}" for r in types.itertuples()) or "none"))
    print(f"report: {REPORT}   (search quality, error types, field completeness)\nnext: python -m src.yt_dataset")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=int, default=TARGET, help="stop at this many fetched videos in total")
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="videos per round; more searches run when fewer than this are waiting")
    ap.add_argument("--comments", type=int, default=COMMENTS, help="top comments (text only) per video, 0 = none")
    ap.add_argument("--workers", type=int, default=WORKERS, help="browsers running at the same time (each has its own 3 s pause); more = faster and more likely to be blocked")
    ap.add_argument("--search-only", action="store_true", help="only run the searches (find videos), fetch nothing")
    ap.add_argument("--max-queries", type=int, help="run at most this many searches in this run (default: as many as needed)")
    ap.add_argument("--report", action="store_true", help="only rewrite docs/youtube_run_report.md from the database")
    ap.add_argument("--years", action=argparse.BooleanOptionalAction, default=True, help="also search '<core term> <year>' (2020-2026)")
    ap.add_argument("--snowball", action="store_true", help="when the queries run out, add related videos of brainrot-titled videos")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    a = ap.parse_args()
    if a.report:
        write_report(db())
        print(f"wrote {REPORT}")
        return
    run(a.target, a.batch_size, a.comments, a.years, a.snowball, a.headed, min(a.workers, 6), a.search_only, a.max_queries)


if __name__ == "__main__":
    main()
