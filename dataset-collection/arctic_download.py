"""
arctic_download.py
Download Reddit comments and posts for selected subreddits from the Arctic Shift
API (https://arctic-shift.photon-reddit.com) into Parquet.

Three modes (can be combined in one run):

  --comments        Deterministic random SAMPLE of comments per subreddit per month,
                    in batches. Batch 1 = ~20,000 comments per subreddit-month.
                    Later, --batch 2 adds ANOTHER ~20,000 that never overlap batch 1.
  --posts           ALL posts (submissions) per subreddit per month.
  --full-months M   ALL comments of the given months (for thread-depth analysis),
                    e.g. --full-months 2012-06,2013-06,...

How the comment sample works (reproducible and extendable):
  * Each month is cut into equal time slots. The slot length is chosen per
    subreddit-month so that one slot holds roughly 1,000 comments.
  * The slots are put into a fixed pseudo-random order derived from a SHA-256
    hash of (seed, subreddit, month, slot number) - the same on every computer.
  * Batch 1 takes slots from the top of that order (every slot is downloaded
    completely) until it has >= --target comments. Batch 2 continues where batch 1
    stopped, and so on. Batches never overlap; all batches together = full month.
  * Subreddit-months with fewer comments than --target are downloaded completely
    in batch 1.
  * The slot length (chosen from the API's monthly comment counts) and the
    positions used by each batch are saved in <out>/_sample_plan.json. Keep this
    file with the data: with it, any batch can be reproduced or extended exactly
    (copy it into a new --out folder before running there).

Output (hive-partitioned Parquet, readable with pandas / DuckDB):
  <out>/comments/subreddit=memes/year=2020/RC_2020-03_b1.parquet   (sample, batch 1)
  <out>/comments_full/subreddit=memes/year=2020/RC_2020-03.parquet  (full months)
  <out>/submissions/subreddit=memes/year=2020/RS_2020-03.parquet    (all posts)
  <out>/_download_log.jsonl       one line per finished subreddit-month
  <out>/_problems.csv             subreddit-months that failed after all retries
  <out>/_sample_plan.json         sampling plan (keep it with the data / on GitHub)

The script is resumable: stop it any time (Ctrl+C) and run the same command again.
Nothing stops the run: failed subreddit-months are retried with back-off and, if
they still fail, logged in _problems.csv and skipped (re-run later to retry them).

Install:  pip install requests pyarrow
Examples:
  python arctic_download.py --out "C:\\reddit_arctic" --comments
  python arctic_download.py --out "C:\\reddit_arctic" --posts
  python arctic_download.py --out "C:\\reddit_arctic" --comments --batch 2
  python arctic_download.py --out "C:\\reddit_arctic" --full-months 2013-06,2016-06,2019-06,2022-06,2025-06
  python arctic_download.py --out "C:\\reddit_arctic" --status
"""

import argparse
import calendar
import csv
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq
import requests

API = "https://arctic-shift.photon-reddit.com"
DEFAULT_SUBREDDITS = ["teenagers", "memes", "todayilearned",
                      "explainlikeimfive", "books", "nosurf"]
SEED = "fightclub-v1"
SLOT_TARGET = 1000                 # aim for ~this many comments per time slot
NICE_MINUTES = [1, 2, 3, 5, 10, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720,
                1440, 2880, 4320, 10080]
MIN_PAGE = 100                     # limit=auto returns >= 100 rows unless the range is exhausted
FLUSH_ROWS = 50_000

COMMENT_FIELDS = ["id", "parent_id", "link_id", "author", "created_utc", "score",
                  "body", "subreddit", "distinguished"]
POST_FIELDS = ["id", "author", "created_utc", "score", "num_comments", "title",
               "selftext", "url", "domain", "is_self", "over_18", "subreddit"]

COMMENT_SCHEMA = pa.schema([
    ("id", pa.string()), ("parent_id", pa.string()), ("link_id", pa.string()),
    ("author", pa.string()), ("created_utc", pa.int64()), ("score", pa.int64()),
    ("body", pa.string()), ("subreddit", pa.string()), ("distinguished", pa.string()),
])
SAMPLE_SCHEMA = COMMENT_SCHEMA.append(pa.field("batch", pa.int16())) \
                              .append(pa.field("slot_start", pa.int64()))
POST_SCHEMA = pa.schema([
    ("id", pa.string()), ("author", pa.string()), ("created_utc", pa.int64()),
    ("score", pa.int64()), ("num_comments", pa.int64()), ("title", pa.string()),
    ("selftext", pa.string()), ("url", pa.string()), ("domain", pa.string()),
    ("is_self", pa.bool_()), ("over_18", pa.bool_()), ("subreddit", pa.string()),
])


# ------------------------------------------------------------------ small helpers
def to_int(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def to_bool(v):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "1")
    return bool(v)


def to_str(v):
    return None if v is None else (v if isinstance(v, str) else str(v))


def row_from(d, fields, schema):
    out = []
    for name, field in zip(fields, schema):
        v = d.get(name)
        if pa.types.is_integer(field.type):
            out.append(to_int(v))
        elif pa.types.is_boolean(field.type):
            out.append(to_bool(v))
        else:
            out.append(to_str(v))
    return out


def month_bounds(ym):
    y, m = map(int, ym.split("-"))
    start = int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp())
    end = start + calendar.monthrange(y, m)[1] * 86400
    return start, end


def month_list(start, end):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def last_full_month():
    now = datetime.now(timezone.utc)
    y, m = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
    return f"{y}-{m:02d}"


def slot_order(seed, sub, ym, n_slots):
    """Fixed pseudo-random order of slot numbers (platform-independent)."""
    key = lambda i: hashlib.sha256(f"{seed}|{sub.lower()}|{ym}|{i}".encode()).hexdigest()
    return sorted(range(n_slots), key=key)


def choose_slot_minutes(month_count, month_minutes):
    if month_count <= 0:
        return month_minutes
    ideal = month_minutes * SLOT_TARGET / month_count
    fitting = [m for m in NICE_MINUTES if m <= ideal]
    return fitting[-1] if fitting else NICE_MINUTES[0]


class Stop(Exception):
    pass


# ------------------------------------------------------------------ HTTP client
class Client:
    """Polite API client: shared rate limit, retries with back-off, 429 handling."""

    def __init__(self, base, min_interval, log, retry_delay=5):
        self.retry_delay = retry_delay
        self.base = base.rstrip("/")
        self.min_interval = min_interval
        self.log = log
        self.lock = threading.Lock()
        self.next_time = 0.0
        self.local = threading.local()
        self.requests = 0
        self.stop = threading.Event()
        self.no_fields = set()          # endpoints that rejected the fields= parameter

    def session(self):
        if not hasattr(self.local, "s"):
            self.local.s = requests.Session()
            self.local.s.headers["User-Agent"] = "fightclub-css-research/1.0 (university project)"
        return self.local.s

    def _wait_turn(self):
        with self.lock:
            now = time.time()
            wait = self.next_time - now
            self.next_time = max(now, self.next_time) + self.min_interval
        if wait > 0:
            time.sleep(wait)

    def get(self, path, params, attempts=8):
        if path in self.no_fields:
            params = {k: v for k, v in params.items() if k != "fields"}
        delay = self.retry_delay
        for attempt in range(1, attempts + 1):
            if self.stop.is_set():
                raise Stop()
            self._wait_turn()
            try:
                r = self.session().get(self.base + path, params=params, timeout=90)
                self.requests += 1
                if r.status_code == 429:
                    reset = to_int(r.headers.get("X-RateLimit-Reset")) or 60
                    self.log(f"rate limited - waiting {reset}s")
                    with self.lock:
                        self.next_time = max(self.next_time, time.time() + reset + 1)
                    continue
                if r.status_code == 400 and "fields" in params:
                    self.no_fields.add(path)
                    self.log(f"server rejected 'fields' on {path}; requesting full records")
                    params = {k: v for k, v in params.items() if k != "fields"}
                    continue
                r.raise_for_status()
                js = r.json()
                if js.get("error"):
                    raise RuntimeError(f"API error: {js['error']}")
                return js.get("data") or []
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                if attempt == attempts:
                    raise
                self.log(f"request failed ({type(exc).__name__}: {str(exc)[:120]}) - "
                         f"retry {attempt}/{attempts - 1} in {delay}s")
                time.sleep(delay)
                delay = min(delay * 2, 300)
        raise RuntimeError("unreachable")

    def fetch_range(self, kind, sub, start, end, fields):
        """Yield every record with start <= created_utc < end, oldest first.
        Robust to either inclusive or exclusive after/before semantics."""
        path = f"/api/{kind}/search"
        cursor, last_ts, boundary_ids, stuck = start - 1, None, set(), 0
        while True:
            page = self.get(path, {"subreddit": sub, "after": cursor, "before": end + 1,
                                   "limit": "auto", "sort": "asc",
                                   "fields": ",".join(fields)})
            new = 0
            for d in page:
                ts = to_int(d.get("created_utc"))
                if ts is None or ts < start or ts >= end:
                    continue
                if last_ts is not None and (ts < last_ts or (ts == last_ts and d.get("id") in boundary_ids)):
                    continue                                   # already yielded
                if ts != last_ts:
                    last_ts, boundary_ids = ts, set()
                boundary_ids.add(d.get("id"))
                new += 1
                yield d
            if len(page) < MIN_PAGE:
                return                                         # range exhausted
            page_last = max(to_int(d.get("created_utc")) or 0 for d in page)
            if page_last >= end:
                return
            if new == 0:
                # a page full of already-seen records from one second: "auto" pages vary in
                # size, so ask again a few times for a bigger page before stepping over it
                stuck += 1
                if stuck <= 5:
                    continue
                self.log(f"r/{sub}: more records in one second than one page holds at "
                         f"{page_last}; some may be skipped")
                cursor, stuck = max(cursor + 1, page_last), 0
                if cursor >= end:
                    return
            else:
                stuck = 0
                cursor = page_last - 1                         # re-read the last second (dedup above)

    def time_series_counts(self, sub, start_ym, end_ym):
        """{YYYY-MM: comment count} from the API's precomputed statistics (fast;
        available from about 2018 on)."""
        s, _ = month_bounds(start_ym)
        _, e = month_bounds(end_ym)
        data = self.get("/api/time_series", {"key": f"r/{sub}/comments/count",
                                              "precision": "month", "after": s, "before": e},
                        attempts=3)
        out = {}
        for b in data:
            t = to_int(b.get("date"))
            if t is None:
                continue
            t = t / 1000 if t > 1e11 else t
            out[datetime.fromtimestamp(t + 2 * 86400, timezone.utc).strftime("%Y-%m")] = to_int(b.get("value")) or 0
        return out

    def month_count(self, sub, ym):
        """Approximate number of comments in one subreddit-month (only used to choose
        the slot length). Tries the aggregate endpoint, then estimates the comment
        rate from three short pages."""
        start, end = month_bounds(ym)
        try:
            data = self.get("/api/comments/search/aggregate",
                            {"aggregate": "created_utc", "frequency": "month",
                             "subreddit": sub, "after": start, "before": end}, attempts=2)
            return sum(to_int(b.get("count")) or 0 for b in data)
        except Stop:
            raise
        except Exception:                                          # noqa: BLE001
            pass
        rates = []
        for k in range(3):
            p0 = start + (end - start) * k // 3
            page = self.get("/api/comments/search",
                            {"subreddit": sub, "after": p0, "before": end, "limit": "auto",
                             "sort": "asc", "fields": "id,created_utc"})
            times = [t for t in (to_int(d.get("created_utc")) for d in page) if t is not None and t < end]
            if len(times) >= MIN_PAGE:
                rates.append(len(times) / max(1, max(times) - p0))
            else:
                rates.append(len(times) / max(1, end - p0))
        return int(sum(rates) / len(rates) * (end - start))


# ------------------------------------------------------------------ output helpers
class Writer:
    def __init__(self, path, schema):
        self.path, self.schema, self.rows, self.n, self.w = path, schema, [], 0, None

    def add(self, row):
        self.rows.append(row)
        self.n += 1
        if len(self.rows) >= FLUSH_ROWS:
            self.flush()

    def flush(self):
        if not self.rows:
            return
        cols = list(zip(*self.rows))
        t = pa.Table.from_arrays([pa.array(list(c), type=f.type) for c, f in zip(cols, self.schema)],
                                 schema=self.schema)
        if self.w is None:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self.w = pq.ParquetWriter(self.path + ".tmp", self.schema, compression="zstd")
        self.w.write_table(t)
        self.rows = []

    def close(self):
        self.flush()
        if self.w is None:                     # no rows: write an empty file so the month counts as done
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            pq.write_table(self.schema.empty_table(), self.path + ".tmp", compression="zstd")
        else:
            self.w.close()
        os.replace(self.path + ".tmp", self.path)

    def abort(self):
        try:
            if self.w:
                self.w.close()
            os.remove(self.path + ".tmp")
        except OSError:
            pass


def part_path(out, folder, sub, ym, name):
    return os.path.join(out, folder, f"subreddit={sub}", f"year={ym[:4]}", name)


# ------------------------------------------------------------------ main program
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output folder, e.g. C:\\reddit_arctic")
    ap.add_argument("--comments", action="store_true", help="download the comment sample")
    ap.add_argument("--posts", action="store_true", help="download all posts")
    ap.add_argument("--full-months", help="comma-separated months to download completely")
    ap.add_argument("--batch", type=int, default=1, help="sample batch number (default 1)")
    ap.add_argument("--target", type=int, default=20000, help="comments per subreddit-month per batch")
    ap.add_argument("--subreddits", default=",".join(DEFAULT_SUBREDDITS))
    ap.add_argument("--start", default="2012-01")
    ap.add_argument("--end", default=last_full_month(), help="last month (default: last full month)")
    ap.add_argument("--workers", type=int, default=2, help="parallel subreddit-months (default 2)")
    ap.add_argument("--min-interval", type=float, default=0.5,
                    help="minimum seconds between API requests overall (default 0.5 = 2/s)")
    ap.add_argument("--api", default=API, help=argparse.SUPPRESS)
    ap.add_argument("--retry-delay", type=float, default=5, help=argparse.SUPPRESS)
    ap.add_argument("--status", action="store_true", help="print a summary and exit")
    args = ap.parse_args()

    out = args.out
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, "_download_log.jsonl")
    plan_path = os.path.join(out, "_sample_plan.json")
    prob_path = os.path.join(out, "_problems.csv")
    print_lock = threading.Lock()

    def say(msg):
        with print_lock:
            print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    def read_log():
        done = {}
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line)
                        done[r["task"]] = r
        return done

    if args.status:
        done = read_log()
        by = {}
        for r in done.values():
            k = (r["mode"], r["status"])
            by[k] = by.get(k, 0) + 1
        for (mode, st), n in sorted(by.items()):
            print(f"{mode:14s} {st:8s} {n:6d} subreddit-months")
        tot = {}
        for r in done.values():
            if r["status"] == "ok":
                tot[r["mode"]] = tot.get(r["mode"], 0) + r.get("rows", 0)
        for mode, n in sorted(tot.items()):
            print(f"{mode:14s} rows: {n:,}")
        return

    if not (args.comments or args.posts or args.full_months):
        ap.error("choose at least one of --comments, --posts, --full-months")

    subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    months = month_list(args.start, args.end)
    client = Client(args.api, args.min_interval, say, args.retry_delay)
    file_lock = threading.Lock()
    done = read_log()

    # clean half-written files from an interrupted run
    removed = 0
    for dp, _, fns in os.walk(out):
        for fn in fns:
            if fn.endswith(".tmp"):
                os.remove(os.path.join(dp, fn))
                removed += 1
    if removed:
        say(f"removed {removed} half-written files from an interrupted run")

    plan = {"seed": SEED, "slot_target": SLOT_TARGET, "target": args.target, "subreddit_months": {}}
    if os.path.exists(plan_path):
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
        if plan.get("target") != args.target or plan.get("seed") != SEED:
            say(f"note: using the saved plan (seed {plan['seed']}, target {plan['target']}) "
                f"for consistency; --target is ignored")
    target = plan["target"]

    def save_plan():
        with open(plan_path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=1, sort_keys=True)
        os.replace(plan_path + ".tmp", plan_path)

    def record(rec):
        with file_lock:
            rec["finished_at"] = datetime.now().isoformat(timespec="seconds")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done[rec["task"]] = rec
            problems = [r for r in done.values() if r["status"] != "ok"]
            with open(prob_path + ".tmp", "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["task", "mode", "subreddit", "month", "status", "error", "finished_at"])
                for r in sorted(problems, key=lambda r: r["task"]):
                    w.writerow([r["task"], r["mode"], r["subreddit"], r["month"], r["status"],
                                r.get("error", ""), r["finished_at"]])
            os.replace(prob_path + ".tmp", prob_path)
            if rec["mode"] == "comments" and rec["status"] == "ok":
                save_plan()

    # ---- comment counts per month (only needed to choose slot lengths)
    ts_counts, ts_lock = {}, threading.Lock()

    def count_for(sub, ym):
        with ts_lock:
            if sub not in ts_counts:
                try:
                    ts_counts[sub] = client.time_series_counts(sub, args.start, args.end)
                except Stop:
                    raise
                except Exception:                                  # noqa: BLE001
                    ts_counts[sub] = {}
        if ym in ts_counts[sub]:
            return ts_counts[sub][ym]
        return client.month_count(sub, ym)

    # ---- task functions -------------------------------------------------------
    def sample_task(sub, ym):
        key = f"{sub}|{ym}"
        start, end = month_bounds(ym)
        month_minutes = (end - start) // 60
        entry = plan["subreddit_months"].get(key)
        if entry is None:
            c = count_for(sub, ym)
            complete = c <= target
            entry = {"count_estimate": c,
                     "slot_minutes": month_minutes if complete else choose_slot_minutes(c, month_minutes),
                     "batches": {}}
            with file_lock:
                plan["subreddit_months"][key] = entry
        slot_s = entry["slot_minutes"] * 60
        n_slots = -(-(end - start) // slot_s)
        earlier = {int(b): v for b, v in entry["batches"].items() if int(b) < args.batch}
        if earlier and max(v["end_pos"] for v in earlier.values()) >= n_slots:
            return {"rows": 0, "note": "month already complete in earlier batches"}
        for b in range(1, args.batch):          # batches must be taken in order
            if b not in earlier:
                raise RuntimeError(f"batch {b} is missing for this month - run --batch {b} first")
        # this batch starts where the previous batch ended (re-running a batch reuses its slots)
        prev_end = max([v["end_pos"] for v in earlier.values()], default=0)
        order = slot_order(plan["seed"], sub, ym, n_slots)
        path = part_path(out, "comments", sub, ym, f"RC_{ym}_b{args.batch}.parquet")
        w = Writer(path, SAMPLE_SCHEMA)
        pos = prev_end
        try:
            while pos < n_slots and w.n < target:
                s0 = start + order[pos] * slot_s
                s1 = min(s0 + slot_s, end)
                for d in client.fetch_range("comments", sub, s0, s1, COMMENT_FIELDS):
                    w.add(row_from(d, COMMENT_FIELDS, COMMENT_SCHEMA) + [args.batch, s0])
                pos += 1
            w.close()
        except BaseException:
            w.abort()
            raise
        with file_lock:
            entry["batches"][str(args.batch)] = {"start_pos": prev_end, "end_pos": pos, "rows": w.n}
        return {"rows": w.n, "slots": pos - prev_end, "slot_minutes": entry["slot_minutes"],
                "complete_month": pos >= n_slots}

    def full_task(kind, folder, prefix, fields, schema, sub, ym):
        start, end = month_bounds(ym)
        w = Writer(part_path(out, folder, sub, ym, f"{prefix}_{ym}.parquet"), schema)
        try:
            for d in client.fetch_range(kind, sub, start, end, fields):
                w.add(row_from(d, fields, schema))
            w.close()
        except BaseException:
            w.abort()
            raise
        return {"rows": w.n}

    tasks = []
    if args.comments:
        tasks += [("comments", f"comments_b{args.batch}|{s}|{ym}", s, ym) for ym in months for s in subs]
    if args.full_months:
        for ym in [m.strip() for m in args.full_months.split(",") if m.strip()]:
            tasks += [("comments_full", f"comments_full|{s}|{ym}", s, ym) for s in subs]
    if args.posts:
        tasks += [("posts", f"posts|{s}|{ym}", s, ym) for ym in months for s in subs]
    todo = [t for t in tasks if done.get(t[1], {}).get("status") != "ok"]
    say(f"{len(tasks)} subreddit-months in total, {len(tasks) - len(todo)} already done, "
        f"{len(todo)} to download  (workers={args.workers}, max {(1 / args.min_interval) if args.min_interval else float('inf'):.1f} requests/s)")

    def run(t):
        mode, task, sub, ym = t
        t0, r0 = time.time(), client.requests
        try:
            if mode == "comments":
                info = sample_task(sub, ym)
            elif mode == "comments_full":
                info = full_task("comments", "comments_full", "RC", COMMENT_FIELDS, COMMENT_SCHEMA, sub, ym)
            else:
                info = full_task("posts", "submissions", "RS", POST_FIELDS, POST_SCHEMA, sub, ym)
            rec = {"task": task, "mode": mode, "subreddit": sub, "month": ym, "status": "ok", **info}
        except Stop:
            return None
        except Exception as exc:                                       # noqa: BLE001
            rec = {"task": task, "mode": mode, "subreddit": sub, "month": ym, "status": "failed",
                   "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
        rec["seconds"] = round(time.time() - t0, 1)
        rec["requests"] = client.requests - r0
        record(rec)
        return rec

    t_start, finished, rows_total = time.time(), 0, 0
    pool = ThreadPoolExecutor(max_workers=max(1, args.workers))
    futures = [pool.submit(run, t) for t in todo]
    try:
        for fut in as_completed(futures):
            rec = fut.result()
            if rec is None:
                continue
            finished += 1
            rows_total += rec.get("rows", 0)
            el = time.time() - t_start
            eta = el / finished * (len(todo) - finished)
            if rec["status"] == "ok":
                extra = f"  ({rec['note']})" if rec.get("note") else ""
                say(f"{rec['mode']:13s} r/{rec['subreddit']:18s} {rec['month']}  {rec['rows']:>9,} rows  "
                    f"{rec['requests']:>5} req  {rec['seconds']:>6.0f}s{extra}   "
                    f"[{finished}/{len(todo)}, ETA {eta / 3600:.1f} h]")
            else:
                say(f"{rec['mode']:13s} r/{rec['subreddit']:18s} {rec['month']}  FAILED: {rec['error']}  "
                    f"(logged in _problems.csv)   [{finished}/{len(todo)}]")
    except KeyboardInterrupt:
        say("stopping... finished subreddit-months are saved; run the same command to resume")
        client.stop.set()
        pool.shutdown(wait=False, cancel_futures=True)
        os._exit(1)
    pool.shutdown(wait=True)

    failed = sum(1 for r in done.values() if r["status"] != "ok")
    say(f"done: {finished} subreddit-months, {rows_total:,} rows, {client.requests:,} requests, "
        f"{(time.time() - t_start) / 3600:.1f} h" + (f"; {failed} problems listed in {prob_path} "
                                                    f"(run the same command again to retry them)" if failed else ""))


if __name__ == "__main__":
    main()