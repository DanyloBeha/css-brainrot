"""Many comments for chosen videos, to see how discussions under brainrot videos changed around the crises (H4).

    caffeinate -i python -m src.yt_comments                              # 1,000 videos, up to 200 top comments each
    python -m src.yt_comments --videos 2000 --per-video 300 --sort both --workers 3
    python -m src.yt_comments --report                                   # only rewrite docs/numbers_youtube_comments.md

Videos: brainrot-titled videos already in the dataset (the Roblox game "Steal a Brainrot" left out; `--which all` takes any video, e.g. as a
control) with at least `--min-comments` comments, the same number per publish year 2020-2026 where a year has enough videos, the rest at
random (seed 42). The chosen videos are stored (`comment_jobs`), a later run continues them (and tries failed ones again); a bigger `--videos` adds videos.
Per video the comment section is scrolled until `--per-video` top-level comments are loaded (about 20 per scroll) for each sort:
    top      YouTube's default order (most liked first)
    newest   newest first (the menu entry "Newest")
Replies are not read (their number is kept). Authors are never read or stored.

Time: YouTube only writes the age of a comment ("3 years ago", rounded down), so `yt_dataset.load_comments` turns it into a posting PERIOD
(`posted_from` .. `posted_to`). Comments older than a year are known to the year only, so the four crisis dates (2020-03-11, 2022-02-24,
2023-10-07, 2025-09-10) separate before and after at year level, not within a year. Other limits: the sample is comments that still exist
(deleted ones are gone), the top sort favours liked comments, and a snapshot of the comment section on the scrape day cannot show how one
discussion changed over time; it compares comments posted in different periods.

The report (docs/numbers_youtube_comments.md, numbers only) counts jobs and comments and gives, per estimated posting year, how many
comments there are, their median length and the share that mention each crisis (lexicons.EVENT_RE) and crisis words in general
(lexicons.CRISIS_RE). A first look, not a test: no claim about change should rest on it before the periods are compared with care.
"""
import argparse
import time

import pandas as pd
from tqdm import tqdm

from .config import ROOT
from .lexicons import CRISIS_RE, EVENT_RE
from .yt_browser import Blocked, Pool, db, now, store_comments
from .yt_dataset import build, clean, load_comments, plain
from .yt_run import log_event

YEARS = range(2020, 2027)
OUT_MD = ROOT / "docs" / "numbers_youtube_comments.md"


def choose_videos(con, n, min_comments, which, seed=42):
    """Store chosen videos as pending jobs until `n` are stored (see the module docstring)."""
    have = {r[0] for r in con.execute("SELECT video_id FROM comment_jobs")}
    need = n - len(have)
    if need <= 0:
        return
    v = build(con)
    v["year"] = v.published_at.dt.year
    pool = v[(v.status == "OK") & (v.comment_count >= min_comments) & ~v.comments_off.fillna(False).astype(bool) & v.year.isin(YEARS) & ~v.video_id.isin(have)]
    if which == "brainrot":
        pool = pool[pool.br & ~pool.game]
    if pool.empty:
        return
    quota = need // len(YEARS)
    pick = pd.concat([g.sample(min(len(g), quota), random_state=seed) for _, g in pool.groupby("year")])
    rest = pool[~pool.video_id.isin(pick.video_id)]
    pick = pd.concat([pick, rest.sample(min(max(need - len(pick), 0), len(rest)), random_state=seed)])
    con.executemany("INSERT INTO comment_jobs VALUES (?,?,?,?,?,?)", [(r.video_id, int(r.year), "pending", None, None, None) for r in pick.itertuples()])
    con.commit()


def run(n=1000, per_video=200, sort="top", min_comments=200, which="brainrot", workers=3, headed=False):
    sorts = ("top", "newest") if sort == "both" else (sort,)
    con = db()
    choose_videos(con, n, min_comments, which)
    todo = [r[0] for r in con.execute("SELECT video_id FROM comment_jobs WHERE status = 'pending' OR status LIKE 'error:%'")]
    run_id = now()
    done, total, bad, bad_in_row, ended, t0 = 0, 0, 0, 0, "finished", time.time()
    print(f"{len(todo)} videos to read ({con.execute('SELECT count(*) FROM comment_jobs').fetchone()[0]} chosen in total), up to {per_video} comments per sort ({'+'.join(sorts)}), {workers} browsers")
    pool = Pool(workers, not headed)
    bar = tqdm(total=len(todo), unit="video", dynamic_ncols=True)
    try:
        for vid in todo:
            pool.submit(("comments", vid, per_video, sorts))
        for _ in todo:
            task, out, err, sec = pool.get()
            vid = task[1]
            if err and err.startswith("blocked"):
                log_event(con, run_id, "comments", vid, "blocked", err, sec)
                raise Blocked(err)
            status, count, got = out if not err else (f"error:{err.split(':')[0]}", None, {})
            n_got = sum(len(c) for c in got.values())
            for srt, cs in got.items():
                store_comments(con, vid, srt, cs)
            con.execute("UPDATE comment_jobs SET status = ?, n_top = ?, n_newest = ?, fetched_at = ? WHERE video_id = ?",
                        (status, len(got.get("top", [])) if "top" in got else None, len(got.get("newest", [])) if "newest" in got else None, now(), vid))
            con.commit()
            log_event(con, run_id, "comments", vid, status, err, sec, n_got)
            bad_in_row = bad_in_row + 1 if (err or status != "OK") else 0
            done, total, bad = done + 1, total + n_got, bad + (status != "OK")
            bar.update(1)
            bar.set_postfix(comments=total, not_ok=bad, comments_per_hour=int(3600 * total / (time.time() - t0)))
            if bad_in_row >= 8:
                raise RuntimeError(f"8 videos in a row without comments (last: {err or status})")
    except Blocked as e:
        ended = "blocked"
        bar.write(f"STOPPED, YouTube asked for a CAPTCHA or reported unusual traffic ({e}). Finished videos are kept; run again later.")
    except KeyboardInterrupt:
        ended = "interrupted"
        bar.write("Interrupted; run the same command to continue.")
    except RuntimeError as e:
        ended = "8 in a row failed"
        bar.write(f"STOPPED: {e}")
    finally:
        bar.close()
        pool.close()
    write_report(con)
    print(f"{ended}: {done} videos read, {total:,} comments, {bad} videos without comments. Report: {OUT_MD}")


# ------------------------------------------------------------------ report
def _block(df):
    return "```\n" + (df.to_string() if len(df) else "(none)") + "\n```\n"


def report_md(con):
    j = pd.read_sql("SELECT * FROM comment_jobs", con)
    out = ["# Comments for the crisis questions\n", "Written by `python -m src.yt_comments`. Numbers only; the design and its limits are in the docstring of `src/yt_comments.py` "
           "(ages are rounded down by YouTube, only comments that still exist, top sort favours liked comments).\n"]
    st = j.assign(read=j.status == "OK").groupby("year").agg(chosen=("video_id", "size"), read=("read", "sum"), pending=("status", lambda x: (x == "pending").sum()))
    out += ["## Videos\n", f"{len(j)} videos chosen; statuses: {j.status.value_counts().to_dict()}\n", _block(st)]
    c = load_comments(con)
    c = c[c.video_id.isin(j.video_id)]
    if c.empty:
        return "\n".join(out)
    t = c.text.map(clean)
    c["words"] = t.str.split().str.len()
    for name, rx in {**EVENT_RE, "crisis_general": CRISIS_RE}.items():
        c[name] = t.str.contains(plain(rx), regex=True)
    per = c.groupby(["video_id", "sort"]).size()
    out += ["## Comments read\n", f"{len(c):,} comments from {c.video_id.nunique()} videos. Comments per video and sort:\n", _block(per.groupby("sort").describe().round(1))]
    cols = list(EVENT_RE) + ["crisis_general"]
    for srt, g in c.groupby("sort"):
        g = g.dropna(subset=["posted_year"])
        by = g.groupby("posted_year").agg(comments=("rank", "size"), videos=("video_id", "nunique"), year_certain_share=("year_certain", "mean"), median_words=("words", "median"))
        for col in cols:
            by[col + "_%"] = (100 * g.groupby("posted_year")[col].mean()).round(2)
        out += [f"## By estimated posting year, sort = {srt}\n", "Share (%) of comments that mention the crisis's words (`lexicons.EVENT_RE`: covid, ukraine, gaza, kirk) or any crisis word. "
                "posted_year = middle of the period YouTube's age allows; year_certain_share = comments whose whole period lies in that year.\n", _block(by.round(2))]
    # by the publish year of the video, to separate the video's age from the comment's age
    by_video = c.merge(j[["video_id", "year"]], on="video_id").groupby(["sort", "year"]).agg(comments=("rank", "size"), median_words=("words", "median"),
                                                                                           **{col + "_%": (col, lambda x: round(100 * x.mean(), 2)) for col in cols})
    out += ["## By the publish year of the video\n", _block(by_video)]
    return "\n".join(out)


def write_report(con):
    OUT_MD.write_text(report_md(con))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--videos", type=int, default=1000, help="videos in total (a later run with a bigger number adds videos)")
    ap.add_argument("--per-video", type=int, default=200, help="comments to load per video and sort")
    ap.add_argument("--sort", choices=["top", "newest", "both"], default="top")
    ap.add_argument("--min-comments", type=int, default=200, help="only videos with at least this many comments")
    ap.add_argument("--which", choices=["brainrot", "all"], default="brainrot", help="brainrot-titled videos only, or any video")
    ap.add_argument("--workers", type=int, default=3, help="browsers at the same time (max 6)")
    ap.add_argument("--report", action="store_true", help="only rewrite the numbers file")
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    if a.report:
        write_report(db())
        print(f"wrote {OUT_MD}")
        return
    run(a.videos, a.per_video, a.sort, a.min_comments, a.which, min(a.workers, 6), a.headed)


if __name__ == "__main__":
    main()
