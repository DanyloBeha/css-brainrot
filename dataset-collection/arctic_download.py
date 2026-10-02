"""
arctic_download.py
Download Reddit comments and posts for selected subreddits from the Arctic Shift
API (https://arctic-shift.photon-reddit.com) into Parquet.

Modes (can be combined in one run):

  --totals          Exact number of comments and posts per subreddit per month
                    (saved in _monthly_totals.csv). Runs first if combined.
  --comments        Deterministic random SAMPLE of comments per subreddit-month,
                    in batches (--target, default 10,000 per batch).
  --posts           Deterministic random SAMPLE of posts per subreddit-month,
                    in batches (--post-target, default 2,000 per batch).
  --all-posts       ALL posts per subreddit-month (slow for big subreddits).
  --full-months M   ALL comments of the given months (for thread-depth analysis),
                    e.g. --full-months 2012-06,2013-06,...
  --batch N         For --comments / --posts: add batch N (another sample of the
                    same size that never overlaps the earlier batches).

How the samples work (reproducible and extendable):
  * Each month is cut into equal time slots. The slot length is chosen per
    subreddit-month so that one slot holds roughly 1,000 comments or 200 posts.
  * The slots are put into a fixed pseudo-random order derived from a SHA-256
    hash of (seed, subreddit, month, slot number) - the same on every computer.
  * Batch 1 takes slots from the top of that order (every slot is downloaded
    completely) until it has >= the target. Batch 2 continues where batch 1
    stopped, and so on. Batches never overlap; all batches together = full month.
  * Subreddit-months with fewer records than the target are downloaded completely
    in batch 1.
  * The slot lengths and the positions used by each batch are saved in
    _sample_plan.json (comments) and _sample_plan_posts.json (posts). Keep these
    files with the data: with them, any batch can be reproduced or extended
    exactly (copy them into a new --out folder before running there).

Output (hive-partitioned Parquet, readable with pandas / DuckDB):
  <out>/comments/subreddit=memes/year=2020/RC_2020-03_b1.parquet      comment sample, batch 1
  <out>/submissions/subreddit=memes/year=2020/RS_2020-03_b1.parquet   post sample, batch 1
  <out>/submissions_full/subreddit=memes/year=2020/RS_2020-03.parquet (--all-posts)
  <out>/comments_full/subreddit=memes/year=2020/RC_2020-03.parquet    (--full-months)
  <out>/_monthly_totals.csv       exact monthly comment and post counts (--totals)
  <out>/_download_log.jsonl       one line per finished task
  <out>/_problems.csv             tasks that failed after all retries
  <out>/_sample_plan*.json        sampling plans (keep them with the data / on GitHub)

The script is resumable: stop it any time (Ctrl+C) and run the same command again.
Nothing stops the run: failed tasks are retried and, if they still fail, logged
in _problems.csv and skipped (run the same command again later to retry them).

Install:  pip install requests pyarrow
Examples:
  python arctic_download.py --out "C:\\reddit_arctic" --totals
  python arctic_download.py --out "C:\\reddit_arctic" --posts
  python arctic_download.py --out "C:\\reddit_arctic" --comments --batch 2
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
POST_SLOT_TARGET = 200             # ... and posts per time slot (more, smaller slots)
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
POST_SAMPLE_SCHEMA = POST_SCHEMA.append(pa.field("batch", pa.int16())) \
                                .append(pa.field("slot_start", pa.int64()))


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


def choose_slot_minutes(month_count, month_minutes, slot_target=SLOT_TARGET):
    if month_count <= 0:
        return month_minutes
    ideal = month_minutes * slot_target / month_count
    fitting = [m for m in NICE_MINUTES if m <= ideal]
    return fitting[-1] if fitting else NICE_MINUTES[0]


class Stop(Exception):
    pass


class ServerTimeout(Exception):
    """HTTP 422 from Arctic Shift: the server gave up on a (too heavy) query."""


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

    def sleep(self, seconds):
        if self.stop.wait(seconds):
            raise Stop()

    def get(self, path, params, attempts=8, raise_422=False):
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
                if r.status_code == 422 and raise_422:
                    raise ServerTimeout()
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
                self.sleep(delay)
                delay = min(delay * 2, 300)
        raise RuntimeError("unreachable")

    def fetch_range(self, kind, sub, start, end, fields):
        """Yield every record with start <= created_utc < end, oldest first.
        Robust to either inclusive or exclusive after/before semantics.

        Arctic Shift answers HTTP 422 when a query takes it too long. Then the same
        request tends to fail again, while a lighter one succeeds. So on a 422 the
        query window is made smaller (down to 1 minute) and the page size switches
        between "auto" and 100; after successes the window grows back. Only if even
        the smallest queries keep failing for ~25 minutes does the month fail."""
        path = f"/api/{kind}/search"
        full_span = end - start + 1
        cursor, last_ts, boundary_ids, stuck = start - 1, None, set(), 0
        span, limit, timeouts, wait = full_span, "auto", 0, self.retry_delay
        while True:
            hi = min(end, cursor + span)                       # query window (cursor, hi]
            try:
                page = self.get(path, {"subreddit": sub, "after": cursor, "before": hi + 1,
                                       "limit": limit, "sort": "asc",
                                       "fields": ",".join(fields)}, raise_422=True)
            except ServerTimeout:
                timeouts += 1
                limit = "100" if limit == "auto" else "auto"
                if span > 60:
                    span = max(60, span // 4)                  # lighter query, try again at once
                    continue
                if timeouts >= 30:
                    raise RuntimeError(f"server keeps timing out (HTTP 422) at {cursor} even for "
                                       f"1-minute queries")
                if timeouts in (6, 15, 25):
                    self.log(f"r/{sub}: server timeouts (HTTP 422) - still retrying with small "
                             f"queries, waiting {wait:.0f}s")
                self.sleep(wait)
                wait = min(wait * 2, 120)
                continue
            timeouts, wait = 0, self.retry_delay
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
            if len(page) < MIN_PAGE:                           # this window is exhausted
                if hi >= end:
                    return
                cursor = hi
                span = min(full_span, span * 2)                # things work: grow the window again
                stuck = 0
                continue
            page_last = max(to_int(d.get("created_utc")) or 0 for d in page)
            if page_last >= end:
                return
            if new == 0:
                # a page full of already-seen records from one second: "auto" pages vary in
                # size, so ask again a few times for a bigger page before stepping over it
                stuck += 1
                if stuck <= 5:
                    limit = "auto"
                    continue
                self.log(f"r/{sub}: more records in one second than one page holds at "
                         f"{page_last}; some may be skipped")
                cursor, stuck = max(cursor + 1, page_last), 0
                if cursor >= end:
                    return
            else:
                stuck = 0
                cursor = page_last - 1                         # re-read the last second (dedup above)

    def time_series_counts(self, sub, start_ym, end_ym, kind="comments"):
        """{YYYY-MM: count} of comments or posts from the API's precomputed monthly
        statistics (fast; available from 2018 on; identical to exact counts)."""
        s, _ = month_bounds(start_ym)
        _, e = month_bounds(end_ym)
        data = self.get("/api/time_series", {"key": f"r/{sub}/{kind}/count",
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

    def exact_count(self, kind, sub, a, b):
        """Exact number of records with a <= created_utc < b from the aggregate
        endpoint. Windows that time out (HTTP 422) are split into 4 smaller ones,
        down to 1 hour; 1-hour windows are retried with waits."""
        path = f"/api/{kind}/search/aggregate"
        total, stack, small_fails, wait, freq = 0, [(a, b)], 0, self.retry_delay, "month"
        while stack:
            x, y = stack.pop()
            try:
                data = self.get(path, {"aggregate": "created_utc", "frequency": freq,
                                       "subreddit": sub, "after": x, "before": y},
                                attempts=4, raise_422=True)
            except ServerTimeout:
                if y - x > 3600:
                    step = -(-(y - x) // 4)
                    stack.extend((z, min(z + step, y)) for z in range(x, y, step))
                    continue
                small_fails += 1
                if small_fails > 20:
                    raise RuntimeError(f"aggregate keeps timing out (HTTP 422) at {x}")
                freq = "day" if freq == "month" else "month"
                self.sleep(wait)
                wait = min(wait * 2, 120)
                stack.append((x, y))
                continue
            total += sum(to_int(r.get("count")) or 0 for r in data)
        return total

    def month_count(self, sub, ym, kind="comments"):
        """Approximate number of comments in one subreddit-month (only used to choose
        the slot length). Tries the aggregate endpoint, then estimates the comment
        rate from three short pages."""
        start, end = month_bounds(ym)
        try:
            data = self.get(f"/api/{kind}/search/aggregate",
                            {"aggregate": "created_utc", "frequency": "month",
                             "subreddit": sub, "after": start, "before": end}, attempts=2)
            return sum(to_int(b.get("count")) or 0 for b in data)
        except Stop:
            raise
        except Exception:                                          # noqa: BLE001
            pass
        # fixed page size (not "auto", whose size varies with server load) so the estimate,
        # and therefore the slot length, is the same every time it is computed
        rates = []
        for k in range(3):
            p0 = start + (end - start) * k // 3
            page = self.get(f"/api/{kind}/search",
                            {"subreddit": sub, "after": p0, "before": end, "limit": 100,
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
    ap.add_argument("--totals", action="store_true", help="exact monthly comment and post counts")
    ap.add_argument("--comments", action="store_true", help="download the comment sample")
    ap.add_argument("--posts", action="store_true", help="download the post sample")
    ap.add_argument("--all-posts", action="store_true", help="download ALL posts (slow)")
    ap.add_argument("--full-months", help="comma-separated months to download completely")
    ap.add_argument("--batch", type=int, default=1, help="sample batch number (default 1)")
    ap.add_argument("--target", type=int, default=10000, help="comments per subreddit-month per batch")
    ap.add_argument("--post-target", type=int, default=2000, help="posts per subreddit-month per batch")
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

    if not (args.totals or args.comments or args.posts or args.all_posts or args.full_months):
        ap.error("choose at least one of --totals, --comments, --posts, --all-posts, --full-months")

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

    # sampling plans: one per kind; a saved plan always wins (keeps batches consistent)
    plan_paths = {"comments": plan_path, "posts": os.path.join(out, "_sample_plan_posts.json")}
    plan_defaults = {"comments": {"seed": SEED, "slot_target": SLOT_TARGET, "target": args.target},
                     "posts": {"seed": SEED + "-posts", "slot_target": POST_SLOT_TARGET,
                               "target": args.post_target}}
    plans = {}
    for kind, path in plan_paths.items():
        plans[kind] = dict(plan_defaults[kind], subreddit_months={})
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                plans[kind] = json.load(f)
            plans[kind].setdefault("slot_target", plan_defaults[kind]["slot_target"])
            wanted = plan_defaults[kind]["target"]
            if (kind == "comments" and args.comments) or (kind == "posts" and args.posts):
                if plans[kind]["target"] != wanted:
                    say(f"note: {kind} sample uses the saved plan's target of "
                        f"{plans[kind]['target']:,} per batch (not {wanted:,}) for consistency")

    def save_plan(kind):
        path = plan_paths[kind]
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(plans[kind], f, indent=1, sort_keys=True)
        os.replace(path + ".tmp", path)

    # ---- monthly totals file
    totals_path = os.path.join(out, "_monthly_totals.csv")
    totals = {}                     # (sub, ym) -> {"comments": (n, source), "posts": (n, source)}
    if os.path.exists(totals_path):
        with open(totals_path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                d = totals.setdefault((r["subreddit"], r["month"]), {})
                for kind in ("comments", "posts"):
                    if r.get(f"{kind}_total", "") != "":
                        d[kind] = (int(r[f"{kind}_total"]), r.get(f"{kind}_source", ""))

    def save_totals():
        with open(totals_path + ".tmp", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["subreddit", "month", "comments_total", "comments_source",
                        "posts_total", "posts_source"])
            for (sub, ym), d in sorted(totals.items()):
                c, p = d.get("comments", ("", "")), d.get("posts", ("", ""))
                w.writerow([sub, ym, c[0], c[1], p[0], p[1]])
        os.replace(totals_path + ".tmp", totals_path)

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
            if rec["mode"] in ("comments", "posts") and rec["status"] == "ok":
                save_plan(rec["mode"])
            if rec["mode"].startswith("totals"):
                save_totals()

    # ---- counts per month (only needed to choose slot lengths)
    ts_counts, ts_lock = {}, threading.Lock()

    def ts_for(kind, sub):
        with ts_lock:
            if (kind, sub) not in ts_counts:
                try:
                    ts_counts[(kind, sub)] = client.time_series_counts(sub, args.start, args.end, kind)
                except Stop:
                    raise
                except Exception:                                  # noqa: BLE001
                    ts_counts[(kind, sub)] = {}
            return ts_counts[(kind, sub)]

    def count_for(kind, sub, ym):
        if kind in totals.get((sub, ym), {}):                     # exact count from --totals
            return totals[(sub, ym)][kind][0]
        ts = ts_for(kind, sub)
        if ym in ts:
            return ts[ym]
        # exact count, so the slot length (and the sample) is the same on every run
        a, b = month_bounds(ym)
        try:
            return client.exact_count(kind, sub, a, b)
        except Stop:
            raise
        except Exception:                                          # noqa: BLE001
            return client.month_count(sub, ym, kind)               # last resort: estimate

    # ---- task functions -------------------------------------------------------
    SAMPLE_KINDS = {
        "comments": ("comments", "RC", COMMENT_FIELDS, COMMENT_SCHEMA, SAMPLE_SCHEMA),
        "posts": ("submissions", "RS", POST_FIELDS, POST_SCHEMA, POST_SAMPLE_SCHEMA),
    }

    def sample_task(kind, sub, ym):
        folder, prefix, fields, schema, sample_schema = SAMPLE_KINDS[kind]
        plan = plans[kind]
        target = plan["target"]
        key = f"{sub}|{ym}"
        start, end = month_bounds(ym)
        month_minutes = (end - start) // 60
        entry = plan["subreddit_months"].get(key)
        if entry is None:
            c = count_for(kind, sub, ym)
            complete = c <= target
            entry = {"count_estimate": c,
                     "slot_minutes": month_minutes if complete else
                     choose_slot_minutes(c, month_minutes, plan["slot_target"]),
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
        path = part_path(out, folder, sub, ym, f"{prefix}_{ym}_b{args.batch}.parquet")
        w = Writer(path, sample_schema)
        pos = prev_end
        try:
            while pos < n_slots and w.n < target:
                s0 = start + order[pos] * slot_s
                s1 = min(s0 + slot_s, end)
                for d in client.fetch_range(kind, sub, s0, s1, fields):
                    w.add(row_from(d, fields, schema) + [args.batch, s0])
                pos += 1
            w.close()
        except BaseException:
            w.abort()
            raise
        with file_lock:
            entry["batches"][str(args.batch)] = {"start_pos": prev_end, "end_pos": pos, "rows": w.n}
        return {"rows": w.n, "slots": pos - prev_end, "slot_minutes": entry["slot_minutes"],
                "complete_month": pos >= n_slots}

    def totals_task(kind, sub):
        """Exact monthly counts: API statistics where available (2018+), else exact
        aggregate counts. Months that fail are retried on the next run."""
        ts = ts_for(kind, sub)
        filled, failed = 0, []
        for ym in months:
            if kind in totals.get((sub, ym), {}):
                continue
            try:
                if ym in ts:
                    val, src = ts[ym], "statistics"
                else:
                    a, b = month_bounds(ym)
                    val, src = client.exact_count(kind, sub, a, b), "exact_count"
            except Stop:
                raise
            except Exception as exc:                               # noqa: BLE001
                failed.append(f"{ym} ({type(exc).__name__})")
                continue
            with file_lock:
                totals.setdefault((sub, ym), {})[kind] = (val, src)
                filled += 1
                if filled % 12 == 0:
                    save_totals()
        if failed:
            raise RuntimeError(f"{len(failed)} months could not be counted: " + ", ".join(failed[:10]))
        return {"rows": filled}

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

    totals_tasks, tasks = [], []
    if args.totals:
        span = f"{args.start}..{args.end}"
        for kind in ("posts", "comments"):
            for s in subs:
                task = f"totals_{kind}|{s}|{span}"
                # done only if every month of this subreddit has a count of this kind
                if done.get(task, {}).get("status") == "ok" and all(
                        kind in totals.get((s, ym), {}) for ym in months):
                    continue
                done.pop(task, None)
                totals_tasks.append((f"totals_{kind}", task, s, span))
    if args.comments:
        tasks += [("comments", f"comments_b{args.batch}|{s}|{ym}", s, ym) for ym in months for s in subs]
    if args.posts:
        tasks += [("posts", f"posts_b{args.batch}|{s}|{ym}", s, ym) for ym in months for s in subs]
    if args.all_posts:
        tasks += [("posts_full", f"posts_full|{s}|{ym}", s, ym) for ym in months for s in subs]
    if args.full_months:
        for ym in [m.strip() for m in args.full_months.split(",") if m.strip()]:
            tasks += [("comments_full", f"comments_full|{s}|{ym}", s, ym) for s in subs]
    todo = [t for t in tasks if done.get(t[1], {}).get("status") != "ok"]
    rate = f"{(1 / args.min_interval) if args.min_interval else float('inf'):.1f}"
    if args.totals:
        say(f"totals: {len(totals_tasks)} subreddit/kind combinations to count "
            f"({len(subs) * 2 - len(totals_tasks)} already complete)")
    if tasks:
        say(f"{len(tasks)} subreddit-months in total, {len(tasks) - len(todo)} already done, "
            f"{len(todo)} to download  (workers={args.workers}, max {rate} requests/s)")

    def run(t):
        mode, task, sub, ym = t
        t0, r0 = time.time(), client.requests
        try:
            if mode in ("comments", "posts"):
                info = sample_task(mode, sub, ym)
            elif mode.startswith("totals_"):
                info = totals_task(mode[len("totals_"):], sub)
            elif mode == "comments_full":
                info = full_task("comments", "comments_full", "RC", COMMENT_FIELDS, COMMENT_SCHEMA, sub, ym)
            else:
                info = full_task("posts", "submissions_full", "RS", POST_FIELDS, POST_SCHEMA, sub, ym)
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

    def run_phase(items):
        nonlocal finished, rows_total
        if not items:
            return
        n0, t0 = finished, time.time()
        pool = ThreadPoolExecutor(max_workers=max(1, args.workers))
        futures = [pool.submit(run, t) for t in items]
        try:
            for fut in as_completed(futures):
                rec = fut.result()
                if rec is None:
                    continue
                finished += 1
                rows_total += rec.get("rows", 0)
                k = finished - n0
                eta = (time.time() - t0) / k * (len(items) - k)
                what = "months counted" if rec["mode"].startswith("totals") else "rows"
                if rec["status"] == "ok":
                    extra = f"  ({rec['note']})" if rec.get("note") else ""
                    say(f"{rec['mode']:15s} r/{rec['subreddit']:18s} {rec['month']}  {rec['rows']:>9,} {what}  "
                        f"{rec['requests']:>5} req  {rec['seconds']:>6.0f}s{extra}   "
                        f"[{k}/{len(items)}, ETA {eta / 3600:.1f} h]")
                else:
                    say(f"{rec['mode']:15s} r/{rec['subreddit']:18s} {rec['month']}  FAILED: {rec['error']}  "
                        f"(logged in _problems.csv)   [{k}/{len(items)}]")
        except KeyboardInterrupt:
            say("stopping... finished work is saved; run the same command to resume")
            client.stop.set()
            pool.shutdown(wait=False, cancel_futures=True)
            os._exit(1)
        pool.shutdown(wait=True)

    run_phase(totals_tasks)          # exact counts first: they also size the post sample's slots
    run_phase(todo)

    failed = sum(1 for r in done.values() if r["status"] != "ok")
    say(f"done: {finished} tasks, {rows_total:,} rows/months, {client.requests:,} requests, "
        f"{(time.time() - t_start) / 3600:.1f} h" + (f"; {failed} problems listed in {prob_path} "
                                                    f"(run the same command again to retry them)" if failed else ""))


if __name__ == "__main__":
    main()