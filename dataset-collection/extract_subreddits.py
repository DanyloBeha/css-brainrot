"""
extract_subreddits.py
Extract selected subreddits from the full monthly Pushshift / Arctic Shift Reddit
dumps (RC_YYYY-MM.zst = comments, RS_YYYY-MM.zst = submissions) into Parquet.

How it works
------------
* Goes month by month, 2012-01 .. 2025-12 by default (whatever files exist).
* Streams each .zst file straight from the source drive: it is decompressed in
  small pieces in memory, never unpacked to disk. The source files are opened
  READ-ONLY and are never modified or deleted.
* Keeps only the rows of the chosen subreddits and only the needed columns.
* Writes one small Parquet file per subreddit per month:
      <out>/comments/subreddit=memes/year=2019/RC_2019-03.parquet
      <out>/submissions/subreddit=memes/year=2019/RS_2019-03.parquet
  DuckDB / Polars read this folder layout directly (hive partitioning).
* Optional --copy-local: copies each month to a temp folder on the laptop first,
  processes it, then DELETES that temporary copy before moving on.
* Optional --mirror: after each month, copies its Parquet files to a second
  folder (e.g. the KINGSTON flash drive). Files are far below FAT32's 4 GB limit.
* Resumable: progress is logged in <out>/_manifest.jsonl. Stop any time
  (Ctrl+C) and run the same command again; finished months are skipped and
  half-written files are cleaned up.
* Detects truncated / broken dump files and marks them in the manifest instead
  of crashing.
* Damaged spots on the source drive: if a file cannot be read to the end, the
  rows read so far are kept and the month is marked "partial". If the drive
  stops responding (no progress for --stall-minutes), that file is stopped and
  marked "stalled". Problem files are retried ONE AT A TIME at the end of the
  run, so they cannot slow down healthy files. Next runs skip them unless
  --redo is given (then they are again processed alone, after everything else).
* --kind comments / submissions and --skip FILE,FILE restrict what is processed.

Install:   pip install zstandard orjson pyarrow
Quick test (first ~200 MB of March 2016, comments + submissions):
    python extract_subreddits.py --src "E:\\pushshift-data-loader\\reddit" --out "C:\\reddit_parquet_test" --only 2016-03 --limit-mb 200
Full run (streams from E:, nothing is copied to the laptop):
    python extract_subreddits.py --src "E:\\pushshift-data-loader\\reddit" --out "C:\\reddit_parquet" --mirror "D:\\reddit_parquet"
Full run, copying each month to the laptop first and deleting it after:
    python extract_subreddits.py --src "E:\\pushshift-data-loader\\reddit" --out "C:\\reddit_parquet" --copy-local --tmp "C:\\reddit_tmp"
Status report:
    python extract_subreddits.py --out "C:\\reddit_parquet" --status
"""

import argparse
import calendar
import json
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
import multiprocessing
import queue as queue_mod
from datetime import datetime, timezone

import orjson
import pyarrow as pa
import pyarrow.parquet as pq
import zstandard

DEFAULT_SUBREDDITS = ["teenagers", "memes", "todayilearned",
                      "explainlikeimfive", "books", "nosurf"]

COMMENT_SCHEMA = pa.schema([
    ("id", pa.string()),
    ("parent_id", pa.string()),
    ("link_id", pa.string()),
    ("author", pa.string()),
    ("created_utc", pa.int64()),
    ("score", pa.int64()),
    ("body", pa.string()),
    ("subreddit", pa.string()),
    ("distinguished", pa.string()),
])

SUBMISSION_SCHEMA = pa.schema([
    ("id", pa.string()),
    ("author", pa.string()),
    ("created_utc", pa.int64()),
    ("score", pa.int64()),
    ("num_comments", pa.int64()),
    ("title", pa.string()),
    ("selftext", pa.string()),
    ("url", pa.string()),
    ("domain", pa.string()),
    ("is_self", pa.bool_()),
    ("over_18", pa.bool_()),
    ("subreddit", pa.string()),
])

CHUNK_BYTES = 64 * 1024 * 1024     # decompressed bytes read at a time
READ_BYTES = 16 * 1024 * 1024      # compressed bytes read from disk at a time
FLUSH_ROWS = 100_000               # rows buffered per subreddit before writing
FILE_RE = re.compile(r"^(RC|RS)_(\d{4})-(\d{2})\.zst$")
MANIFEST = "_manifest.jsonl"


# ----------------------------------------------------------------- helpers
def to_int(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    if isinstance(v, str):
        return v.lower() in ("true", "1")
    return bool(v)


def to_str(v):
    if v is None:
        return None
    return v if isinstance(v, str) else str(v)


def comment_row(d):
    return (to_str(d.get("id")), to_str(d.get("parent_id")), to_str(d.get("link_id")),
            to_str(d.get("author")), to_int(d.get("created_utc")), to_int(d.get("score")),
            to_str(d.get("body")), to_str(d.get("subreddit")), to_str(d.get("distinguished")))


def submission_row(d):
    return (to_str(d.get("id")), to_str(d.get("author")), to_int(d.get("created_utc")),
            to_int(d.get("score")), to_int(d.get("num_comments")), to_str(d.get("title")),
            to_str(d.get("selftext")), to_str(d.get("url")), to_str(d.get("domain")),
            to_bool(d.get("is_self")), to_bool(d.get("over_18")), to_str(d.get("subreddit")))


def month_end_ts(year, month):
    last = calendar.monthrange(year, month)[1]
    return int(datetime(year, month, last, 23, 59, 59, tzinfo=timezone.utc).timestamp())


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024


def source_was_missing(rec):
    """True for records written because the source drive was unplugged
    (status 'source_missing', or older 'error' records with a missing path)."""
    if rec.get("status") == "source_missing":
        return True
    err = rec.get("error") or ""
    return rec.get("status") == "error" and (
        "FileNotFoundError" in err or "cannot find the path" in err
        or "No such file or directory" in err)


class SourceMissing(Exception):
    """The source drive/folder disappeared while a file was being processed."""


def read_manifest(out_dir):
    done = {}
    path = os.path.join(out_dir, MANIFEST)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    if source_was_missing(rec):
                        continue              # drive was unplugged: not a real result
                    done[rec["file"]] = rec   # later records win
    return done


def append_manifest(out_dir, rec):
    with open(os.path.join(out_dir, MANIFEST), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def remove_tmp_files(root):
    """Delete half-written *.tmp files left by an interrupted run."""
    n = 0
    if not os.path.isdir(root):
        return 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn.endswith(".tmp"):
                os.remove(os.path.join(dirpath, fn))
                n += 1
    return n


# ----------------------------------------------------------------- worker
class MonthWriter:
    """One Parquet writer per subreddit for a single month, written to *.tmp
    and renamed only when the whole month finished."""

    def __init__(self, out_dir, kind, prefix, year, month, schema):
        self.out_dir, self.kind, self.schema = out_dir, kind, schema
        self.year, self.name = year, f"{prefix}_{year}-{month:02d}.parquet"
        self.buffers, self.writers, self.counts = {}, {}, {}

    def path(self, sub):
        d = os.path.join(self.out_dir, self.kind, f"subreddit={sub}", f"year={self.year}")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, self.name)

    def add(self, sub, row):
        buf = self.buffers.setdefault(sub, [])
        buf.append(row)
        self.counts[sub] = self.counts.get(sub, 0) + 1
        if len(buf) >= FLUSH_ROWS:
            self.flush(sub)

    def flush(self, sub):
        rows = self.buffers.get(sub)
        if not rows:
            return
        cols = list(zip(*rows))
        table = pa.Table.from_arrays(
            [pa.array(list(c), type=f.type) for c, f in zip(cols, self.schema)],
            schema=self.schema)
        if sub not in self.writers:
            self.writers[sub] = pq.ParquetWriter(self.path(sub) + ".tmp", self.schema,
                                                 compression="zstd")
        self.writers[sub].write_table(table)
        self.buffers[sub] = []

    def close(self):
        final = []
        for sub in list(self.buffers):
            self.flush(sub)
        for sub, w in self.writers.items():
            w.close()
            dst = self.path(sub)
            os.replace(dst + ".tmp", dst)
            final.append(dst)
        return final

    def abort(self):
        for sub, w in self.writers.items():
            try:
                w.close()
            except Exception:
                pass
            try:
                os.remove(self.path(sub) + ".tmp")
            except OSError:
                pass


def process_file(job, progress=None):
    """Runs in a worker process: one attempt at one dump file. Retrying is
    handled by the main process (failed files are retried alone at the end)."""
    rec = _process_once(job, progress)
    return rec


def _worker_main(job, progress, results):
    """Entry point of a worker process."""
    _ignore_ctrl_c()
    try:
        rec = process_file(job, progress)
    except BaseException as exc:                               # noqa: BLE001
        missing = not os.path.exists(job[0])
        rec = {"file": os.path.basename(job[0]), "status": "source_missing" if missing else "error",
               "error": f"worker crashed: {type(exc).__name__}: {exc}", "rows": {},
               "outputs": [], "seconds": 0}
    results.put(rec)


def _ignore_ctrl_c():
    """Workers ignore Ctrl+C; the main process stops them cleanly."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _process_once(job, progress=None):
    """One attempt at one dump file. Returns a manifest record."""
    src, out_dir, subs, limit_mb, copy_local, tmp_dir = job
    fname = os.path.basename(src)
    prefix, year, month = FILE_RE.match(fname).groups()
    year, month = int(year), int(month)
    kind = "comments" if prefix == "RC" else "submissions"
    schema = COMMENT_SCHEMA if prefix == "RC" else SUBMISSION_SCHEMA
    to_row = comment_row if prefix == "RC" else submission_row
    wanted = {s.lower(): s for s in subs}
    # Fast pre-filter on raw bytes; every hit is then parsed and checked properly
    # (this also drops crossposts that only mention the subreddit). Case-sensitive
    # regex is ~2x faster than case-insensitive, so common spellings are listed.
    spellings = sorted({v for x in subs for v in (x, x.lower(), x.capitalize())}, key=len, reverse=True)
    pattern = re.compile(rb'"subreddit": ?"(?:' +
                         b"|".join(re.escape(v.encode()) for v in spellings) + rb')"')
    t0 = time.time()
    local_copy = None
    writer = MonthWriter(out_dir, kind, prefix, year, month, schema)
    status, error = "ok", None
    hits = bad_json = 0
    first_ts = last_ts = None
    decompressed = 0
    try:
        read_path = src
        if copy_local:
            size = os.path.getsize(src)
            free = shutil.disk_usage(tmp_dir).free
            if free < size + 10 * 1024**3:
                raise RuntimeError(f"not enough space in {tmp_dir} to copy {fname} "
                                   f"({fmt_bytes(size)} needed, {fmt_bytes(free)} free)")
            candidate = os.path.join(tmp_dir, fname)
            if os.path.exists(candidate) and os.path.samefile(candidate, src):
                raise RuntimeError("--tmp points at the source folder; refusing to copy")
            local_copy = candidate          # only ever a copy, never the source
            shutil.copyfile(src, local_copy)
            read_path = local_copy

        limit = limit_mb * 1024 * 1024 if limit_mb else None

        def take(line):
            nonlocal hits, bad_json
            try:
                d = orjson.loads(line)
            except orjson.JSONDecodeError:
                bad_json += 1
                return
            sub = str(d.get("subreddit", "")).lower()
            if sub in wanted:
                writer.add(wanted[sub], to_row(d))
                hits += 1

        def line_ts(line):
            try:
                return to_int(orjson.loads(line).get("created_utc"))
            except Exception:                              # noqa: BLE001
                return None

        # Large sequential reads (16 MB) so parallel workers don't make the
        # hard drive jump between files every 128 KB.
        with open(read_path, "rb", buffering=READ_BYTES) as fh:  # read-only
            reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(
                fh, read_size=READ_BYTES)
            leftover = b""
            while True:
                try:
                    chunk = reader.read(CHUNK_BYTES)
                except OSError as read_err:
                    if not os.path.exists(src):
                        raise SourceMissing(str(read_err)) from read_err
                    # The drive could not read this part of the file. Keep every
                    # row read so far (the file is ordered by time) and flag it.
                    status = "partial"
                    upto = (datetime.fromtimestamp(last_ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                            if last_ts else "start of month")
                    error = (f"read error on the source drive after {decompressed / 1e9:.1f} GB "
                             f"decompressed; data kept up to {upto} ({read_err})")
                    break
                if not chunk:
                    break
                decompressed += len(chunk)
                if progress is not None:
                    progress.value = decompressed
                first_nl = chunk.find(b"\n")
                if first_nl == -1:
                    leftover += chunk
                    continue
                # the record that was split between the previous chunk and this one
                head = leftover + chunk[:first_nl]
                if first_ts is None:
                    first_ts = line_ts(head)
                if pattern.search(head):
                    take(head)
                last_nl = chunk.rfind(b"\n")
                start = first_nl + 1
                # scan the complete records of this chunk in place (no copying)
                prev = -1
                for m in pattern.finditer(chunk, start, last_nl):
                    s = chunk.rfind(b"\n", 0, m.start()) + 1
                    if s == prev:
                        continue
                    prev = s
                    take(chunk[s:chunk.find(b"\n", s)])
                # timestamp of the last complete record (truncation check)
                p = chunk.rfind(b"\n", 0, last_nl)
                ts = line_ts(chunk[p + 1:last_nl] if p >= start - 1 else head)
                if ts:
                    last_ts = ts if last_ts is None else max(last_ts, ts)
                leftover = chunk[last_nl + 1:]
                if limit and decompressed >= limit:
                    status = "partial_test"
                    break

            # whatever is left after the last newline
            if status == "ok" and leftover.strip():
                try:
                    orjson.loads(leftover)
                    take(leftover)
                except orjson.JSONDecodeError:
                    status = "truncated"
                    error = "file ends in the middle of a record"

        if status == "ok" and last_ts is not None and last_ts < month_end_ts(year, month) - 2 * 86400:
            status = "truncated"
            error = ("data stops at " +
                     datetime.fromtimestamp(last_ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
        written = writer.close()
    except Exception as exc:                                   # noqa: BLE001
        writer.abort()
        if isinstance(exc, SourceMissing) or (isinstance(exc, OSError) and not os.path.exists(src)):
            return {"file": fname, "kind": kind, "status": "source_missing",
                    "error": f"source file not reachable: {exc}", "rows": {}, "outputs": [],
                    "seconds": round(time.time() - t0, 1)}
        tb = traceback.extract_tb(exc.__traceback__)
        where = f" (at line {tb[-1].lineno}: {tb[-1].line})" if tb else ""
        status, error, written = "error", f"{type(exc).__name__}: {exc}{where}", []
    finally:
        if local_copy and os.path.exists(local_copy):
            os.remove(local_copy)                              # delete temporary copy

    return {
        "file": fname, "kind": kind, "status": status, "error": error,
        "rows": writer.counts, "rows_total": hits,
        "bad_json": bad_json, "decompressed_gb": round(decompressed / 1e9, 2),
        "compressed_gb": round(_size(src) / 1e9, 2),
        "first_ts": first_ts, "last_ts": last_ts,
        "seconds": round(time.time() - t0, 1), "outputs": written,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


# ----------------------------------------------------------------- main
def mirror_files(paths, out_dir, mirror_dir):
    for p in paths:
        rel = os.path.relpath(p, out_dir)
        dst = os.path.join(mirror_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(p, dst + ".tmp")
        os.replace(dst + ".tmp", dst)


def collect_jobs(src, start, end, only):
    files, missing = [], []
    ym = []
    y, m = start
    while (y, m) <= end:
        ym.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    if only:
        ym = [x for x in ym if f"{x[0]}-{x[1]:02d}" in only]
    for y, m in ym:
        for prefix, folder in (("RS", "submissions"), ("RC", "comments")):
            name = f"{prefix}_{y}-{m:02d}.zst"
            candidates = [os.path.join(src, folder, name), os.path.join(src, name)]
            found = next((c for c in candidates if os.path.exists(c)), None)
            (files.append(found) if found else missing.append(name))
    return files, missing


def print_status(out_dir):
    done = read_manifest(out_dir)
    if not done:
        print("No manifest found in", out_dir)
        return
    by_status, totals = {}, {}
    for rec in done.values():
        by_status.setdefault(rec["status"], []).append(rec["file"])
        for sub, n in rec.get("rows", {}).items():
            key = (rec["kind"], sub)
            totals[key] = totals.get(key, 0) + n
    for st, files in sorted(by_status.items()):
        print(f"{st:13s} {len(files):4d} files" +
              ("" if st == "ok" else ":  " + ", ".join(sorted(files))))
    print("\nRows extracted:")
    for (kind, sub), n in sorted(totals.items()):
        print(f"  {kind:12s} {sub:20s} {n:>14,}")


def check_source_is_protected(args):
    """Refuse to run if any folder the script writes to (or cleans up) is on the
    source drive, inside the source folder, or contains it. The dump files are
    only ever opened read-only; this guard makes accidental writes impossible."""
    src = os.path.realpath(args.src)
    src_drive = os.path.splitdrive(src)[0].upper()
    targets = {"--out": args.out, "--mirror": args.mirror}
    if args.copy_local:
        targets["--tmp"] = args.tmp
    for flag, path in targets.items():
        if not path:
            continue
        p = os.path.realpath(path)
        same_drive = src_drive and os.path.splitdrive(p)[0].upper() == src_drive
        try:
            nested = os.path.commonpath([src, p]) in (src, p)
        except ValueError:          # Windows: paths on different drives
            nested = False
        if same_drive or nested:
            sys.exit(f"Refusing to run: {flag} ({path}) is on the same drive as, or inside, "
                     f"the source folder ({args.src}). Choose a folder on another drive so "
                     f"the source stays untouched.")


def parse_ym(s):
    y, m = s.split("-")
    return int(y), int(m)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help="folder with comments/ and submissions/ (or the .zst files)")
    ap.add_argument("--out", required=True, help="output folder for Parquet files")
    ap.add_argument("--mirror", help="second output folder, e.g. the flash drive")
    ap.add_argument("--subreddits", default=",".join(DEFAULT_SUBREDDITS))
    ap.add_argument("--start", default="2012-01", help="first month, YYYY-MM")
    ap.add_argument("--end", default="2025-12", help="last month, YYYY-MM")
    ap.add_argument("--only", help="comma-separated months to process, e.g. 2016-03,2020-09")
    ap.add_argument("--workers", type=int, default=2,
                    help="months processed in parallel (2 suits a USB hard drive)")
    ap.add_argument("--copy-local", action="store_true",
                    help="copy each month to --tmp first and delete the copy after")
    ap.add_argument("--tmp", default=tempfile.gettempdir(), help="temp folder for --copy-local")
    ap.add_argument("--limit-mb", type=int, default=0,
                    help="TEST ONLY: stop after this many decompressed MB per file")
    ap.add_argument("--redo", action="store_true",
                    help="also re-process files marked truncated/error/partial/stalled")
    ap.add_argument("--kind", choices=["both", "comments", "submissions"], default="both",
                    help="process only comments (RC) or only submissions (RS)")
    ap.add_argument("--skip", help="comma-separated dump files to leave out, e.g. RS_2017-01.zst")
    ap.add_argument("--stall-minutes", type=float, default=15,
                    help="stop a file that makes no progress for this long (default 15)")
    ap.add_argument("--status", action="store_true", help="print progress summary and exit")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if args.status:
        print_status(args.out)
        return
    if not args.src:
        ap.error("--src is required")

    check_source_is_protected(args)
    subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    only = set(x.strip() for x in args.only.split(",")) if args.only else None
    files, missing = collect_jobs(args.src, parse_ym(args.start), parse_ym(args.end), only)

    cleaned = remove_tmp_files(args.out) + (remove_tmp_files(args.mirror) if args.mirror else 0)
    if args.copy_local and os.path.isdir(args.tmp):
        for fn in os.listdir(args.tmp):          # leftover month copies (never the source:
            if FILE_RE.match(fn):                # --tmp is refused on the source drive)
                os.remove(os.path.join(args.tmp, fn))
                cleaned += 1
    if cleaned:
        print(f"Removed {cleaned} half-written .tmp files from an earlier interrupted run.")

    done = read_manifest(args.out)
    problem = {"error", "stalled", "partial"}
    # test runs ("partial_test") never count as finished
    skip_status = {"ok"} if args.redo else {"ok", "truncated"} | problem
    if args.limit_mb:
        skip_status = set()                  # test runs always re-run
    skip_files = set(x.strip() for x in args.skip.split(",")) if args.skip else set()
    todo = [f for f in files
            if done.get(os.path.basename(f), {}).get("status") not in skip_status
            and os.path.basename(f) not in skip_files
            and (args.kind == "both" or os.path.basename(f).startswith(
                "RC_" if args.kind == "comments" else "RS_"))]
    # Files that failed before are processed ALONE at the end, so a damaged spot
    # on the drive cannot slow down the healthy files running next to it.
    solo = [f for f in todo if done.get(os.path.basename(f), {}).get("status") in problem]
    main_q = [f for f in todo if f not in solo]
    sizes = {f: _size(f) for f in todo}
    todo_bytes = sum(sizes.values())

    print(f"Subreddits : {', '.join(subs)}")
    print(f"Months     : {args.start} .. {args.end}   ({args.kind})")
    print(f"Files found: {len(files)}  |  to process: {len(todo)} ({fmt_bytes(todo_bytes)} compressed)"
          + (f", {len(solo)} earlier failures retried alone at the end" if solo else ""))
    if missing:
        print(f"Missing    : {len(missing)} files not on disk: " + ", ".join(missing[:12]) +
              (" ..." if len(missing) > 12 else ""))
    if args.mirror:
        os.makedirs(args.mirror, exist_ok=True)
        print(f"Mirror     : {args.mirror}")
    print(f"Watchdog   : a file with no progress for {args.stall_minutes:g} min is stopped "
          f"and retried alone at the end")
    print()

    ctx = multiprocessing.get_context("spawn")
    results = ctx.Queue()
    running = {}        # file name -> dict(proc, src, progress, last, since, phase)
    state = {"bytes_done": 0, "t_start": time.time()}
    stall_s = args.stall_minutes * 60

    def job_for(src):
        return (src, args.out, subs, args.limit_mb, args.copy_local, args.tmp)

    def start(src, phase):
        progress = ctx.Value("q", 0)
        proc = ctx.Process(target=_worker_main, args=(job_for(src), progress, results), daemon=True)
        proc.start()
        running[os.path.basename(src)] = {"proc": proc, "src": src, "progress": progress,
                                          "last": 0, "since": time.time(), "phase": phase,
                                          "t0": time.time()}

    def finish(rec, phase):
        """Record a result. In the main phase, failures are queued for a solo retry."""
        info = running.pop(rec["file"], None)
        src = info["src"] if info else None
        if info:
            info["proc"].join(timeout=10)
        if rec.get("status") == "source_missing":
            # Drive unplugged: nothing is recorded; the file goes back in the queue.
            if src:
                (main_q if phase == "main" else solo).insert(0, src)
            state["source_lost"] = True
            print(f"[{time.strftime('%H:%M:%S')}] {rec['file']:18s} source drive not reachable "
                  f"- will be processed again", flush=True)
            return
        if args.limit_mb:
            rec["status"] = "partial_test"
        if phase == "main" and rec["status"] in problem and src:
            solo.append(src)
            rec["note"] = "will be retried alone at the end"
        if args.mirror and rec.get("outputs"):
            try:
                mirror_files(rec["outputs"], args.out, args.mirror)
            except Exception as exc:                  # noqa: BLE001
                rec["mirror_error"] = f"{type(exc).__name__}: {exc}"
        append_manifest(args.out, rec)
        if src and not rec.get("note"):
            state["bytes_done"] += sizes.get(src, 0)
        elapsed = time.time() - state["t_start"]
        bd = state["bytes_done"]
        eta = elapsed / bd * (todo_bytes - bd) if bd else 0
        rows = ", ".join(f"{k}={v:,}" for k, v in sorted(rec.get("rows", {}).items())) or "no rows"
        flag = "" if rec["status"] in ("ok", "partial_test") else \
            f"  <-- {rec['status'].upper()}: {rec.get('error')}"
        if rec.get("note"):
            flag += f"  [{rec['note']}]"
        print(f"[{time.strftime('%H:%M:%S')}] {rec['file']:18s} {rec.get('seconds', 0):>7.0f}s  "
              f"{rows}{flag}")
        if rec.get("mirror_error"):
            print(f"    mirror copy failed: {rec['mirror_error']}")
        print(f"    progress {fmt_bytes(bd)} / {fmt_bytes(todo_bytes)}  ETA {eta / 3600:.1f} h",
              flush=True)

    def watchdog():
        now = time.time()
        for name, info in list(running.items()):
            val = info["progress"].value
            if val != info["last"]:
                info["last"], info["since"] = val, now
            elif now - info["since"] > stall_s:
                info["proc"].terminate()
                info["proc"].join(timeout=30)
                # remove this file's half-written outputs
                stem = name.replace(".zst", ".parquet.tmp")
                for root in (args.out, args.mirror):
                    if root and os.path.isdir(root):
                        for dp, _, fns in os.walk(root):
                            if stem in fns:
                                os.remove(os.path.join(dp, stem))
                finish({"file": name, "kind": "comments" if name.startswith("RC_") else "submissions",
                        "status": "stalled", "rows": {}, "outputs": [],
                        "seconds": round(now - info["t0"], 1),
                        "error": f"no progress for {args.stall_minutes:g} min after "
                                 f"{val / 1e9:.1f} GB decompressed (the drive stopped responding)",
                        "finished_at": datetime.now().isoformat(timespec="seconds")},
                       info["phase"])
            elif not info["proc"].is_alive() and info["proc"].exitcode not in (0, None):
                finish({"file": name, "status": "error", "rows": {}, "outputs": [],
                        "error": f"worker exited with code {info['proc'].exitcode}",
                        "seconds": round(now - info["t0"], 1)}, info["phase"])

    def wait_for_source():
        """Pause while the source drive is unplugged; continue when it is back."""
        if os.path.isdir(args.src) and not state.get("source_lost"):
            return
        if running:                         # let the other workers finish/fail first
            return
        if not os.path.isdir(args.src):
            print(f"\n[{time.strftime('%H:%M:%S')}] Source folder {args.src} is not reachable. "
                  f"Plug the drive back in (it must get the same drive letter); "
                  f"processing continues automatically. Ctrl+C to stop.", flush=True)
            while not os.path.isdir(args.src):
                time.sleep(10)
            time.sleep(15)                  # give Windows a moment to mount it fully
            print(f"[{time.strftime('%H:%M:%S')}] Source is back - continuing.\n", flush=True)
        state["source_lost"] = False

    def drain(phase, limit_workers):
        queue = main_q if phase == "main" else solo
        while queue or running:
            wait_for_source()
            while queue and len(running) < limit_workers and not state.get("source_lost"):
                start(queue.pop(0), phase)
            try:
                rec = results.get(timeout=5)
                finish(rec, running.get(rec["file"], {}).get("phase", phase))
            except queue_mod.Empty:
                pass
            watchdog()

    try:
        drain("main", max(1, args.workers))
        if solo:
            print(f"\nRetrying {len(solo)} problem file(s) one at a time...\n", flush=True)
            drain("solo", 1)
    except KeyboardInterrupt:
        # Stop immediately; half-written .tmp files are removed on the next start.
        print("\nStopping... finished months are saved; run the same command to resume.",
              flush=True)
        for info in running.values():
            try:
                info["proc"].terminate()
            except Exception:                         # noqa: BLE001
                pass
        os._exit(1)

    print()
    print_status(args.out)


if __name__ == "__main__":
    main()