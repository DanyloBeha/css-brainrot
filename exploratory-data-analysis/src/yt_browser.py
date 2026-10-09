"""Browser scraper for YouTube metadata (Playwright + Chromium, public pages only, no login).

Steps (each resumable, state lives in data/external/raw/yt_scrape/yt.sqlite, which is git-ignored):
    python -m src.yt_run                                  # the usual way: search + detail together, progress bar, live CSV (see yt_run.py)
    python -m src.yt_browser search [--terms brainrot skibidi] [--sorts views date] [--max-results 500] [--years]
    python -m src.yt_browser detail [--limit 300] [--comments 20]   # watch page of every video found and not yet fetched
    python -m src.yt_browser report                      # what is in the database

`search` scrolls the search results page of a term (sort by view count or upload date) and stores every video it shows, with the
APPROXIMATE numbers the list shows ("1.2M views", "3 years ago"). `detail` opens the watch page of each video and stores the JSON
the page embeds (player response and page data): exact view count, publish date, tags, duration, likes where shown. Raw JSON is kept,
so the parsing in `yt_dataset.py` can be redone without fetching again.

Politeness: one tab, DELAY seconds between page loads, no login, no proxies. A CAPTCHA / "unusual traffic" page stops the run (Blocked).
Search pages and the internal API are disallowed in YouTube's robots.txt and automated access is against its Terms of Service:
this was decided by Ivan on 2026-10-05 (see docs/research_log.md).
"""
import argparse
import json
import sqlite3
import time
import zlib
from datetime import datetime, timezone

from .config import EXT

RAW = EXT / "raw" / "yt_scrape"
DB = RAW / "yt.sqlite"
DELAY = 3.0                                  # seconds between page loads
PARSER_VERSION = 3
SORT = {"views": "CAMSAhAB", "date": "CAISAhAB", "relevance": "EgIQAQ%3D%3D"}      # `sp` codes: sort + "videos only"
QUERIES = {                                  # plain search strings; the tier names follow src/lexicons.py (brainrot terms are NOT extended here)
    "core": ["brainrot", "brain rot", "skibidi"],
    "extended": ["rizz", "gyatt", "fanum tax", "mewing", "tralalero", "tung tung"],
    "ambiguous": ["sigma"],
}


class Blocked(RuntimeError):
    """YouTube asked for a CAPTCHA or reported unusual traffic: stop, do not try to get around it."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db():
    RAW.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS hits (video_id TEXT, term TEXT, sort TEXT, rank INTEGER, fetched_at TEXT, source TEXT, title TEXT,
                                         channel_id TEXT, channel TEXT, views_text TEXT, age_text TEXT, length_text TEXT,
                                         PRIMARY KEY (video_id, term, sort));
        CREATE TABLE IF NOT EXISTS searches (term TEXT, sort TEXT, fetched_at TEXT, results INTEGER, reached_end INTEGER, seconds REAL,
                                             PRIMARY KEY (term, sort));
        CREATE TABLE IF NOT EXISTS videos (video_id TEXT PRIMARY KEY, fetched_at TEXT, parser_version INTEGER, status TEXT, raw BLOB);
        CREATE TABLE IF NOT EXISTS comments (video_id TEXT, rank INTEGER, text TEXT, likes_text TEXT, PRIMARY KEY (video_id, rank));
        CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, started_at TEXT, ended_at TEXT, workers INTEGER, batch_size INTEGER, target INTEGER,
                                         comments INTEGER, ended_by TEXT);
        CREATE TABLE IF NOT EXISTS comments2 (video_id TEXT, sort TEXT, rank INTEGER, text TEXT, likes_text TEXT, age_text TEXT, replies_text TEXT,
                                              pinned INTEGER, hearted INTEGER, edited INTEGER, fetched_at TEXT, PRIMARY KEY (video_id, sort, rank));
        CREATE TABLE IF NOT EXISTS comment_jobs (video_id TEXT PRIMARY KEY, year INTEGER, status TEXT, n_top INTEGER, n_newest INTEGER, fetched_at TEXT);
        CREATE TABLE IF NOT EXISTS edges (src TEXT, dst TEXT, pos INTEGER, PRIMARY KEY (src, dst));
        CREATE TABLE IF NOT EXISTS related_seeds (src TEXT PRIMARY KEY, year INTEGER, matched TEXT, status TEXT, fetched_at TEXT);
        CREATE TABLE IF NOT EXISTS related (src TEXT, pos INTEGER, dst TEXT, title TEXT, channel TEXT, views_text TEXT, age_text TEXT, PRIMARY KEY (src, pos));
        CREATE TABLE IF NOT EXISTS log (run_id TEXT, ts TEXT, kind TEXT, key TEXT, status TEXT, error TEXT, seconds REAL, results INTEGER, note TEXT);
    """)
    if not con.execute("SELECT 1 FROM comments2 LIMIT 1").fetchone():          # first top-10 comments (no age, replies ...) move to the new table once
        con.execute("INSERT OR IGNORE INTO comments2 (video_id, sort, rank, text, likes_text) SELECT video_id, 'top', rank, text, likes_text FROM comments")
        con.commit()
    return con


# ------------------------------------------------------------------ browser
class Browser:
    """Context manager: one Chromium tab, English interface, DELAY seconds between loads, consent dialog handled."""

    def __init__(self, headless=True):
        self.headless, self.last = headless, 0.0

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=self.headless)
        self.ctx = self.browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
        self.page = self.ctx.new_page()
        return self

    def __exit__(self, *exc):
        self.browser.close()
        self._pw.stop()

    def goto(self, url):
        wait = self.last + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        self.page.goto(url, wait_until="domcontentloaded")
        self.last = time.time()
        self._consent()
        self._check_block()

    def _consent(self):
        """EU-style 'Before you continue' page: press 'Reject all' (no cookies wanted), then wait for the real page."""
        if "consent." in self.page.url:
            self.page.get_by_role("button", name="Reject all").first.click()
            self.page.wait_for_load_state("domcontentloaded")

    def _check_block(self):
        if "/sorry/" in self.page.url or self.page.locator("text=unusual traffic").count():
            raise Blocked(f"blocked at {self.page.url}")


# ------------------------------------------------------------------ search page
def _walk(node, key):
    """Every dict stored under `key` anywhere in a nested JSON structure."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield v
            else:
                yield from _walk(v, key)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v, key)


def _text(x):
    if not x:
        return None
    return x.get("simpleText") or "".join(r.get("text", "") for r in x.get("runs", [])) or None


def _lockup_video(r):
    """Video dict from a `lockupViewModel` (the layout used for result and recommendation cards), None for playlists, channels and mixes."""
    if r.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO":
        return None
    meta = r.get("metadata", {}).get("lockupMetadataViewModel", {})
    rows = [p.get("text", {}).get("content") for m in meta.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", []) for p in m.get("metadataParts", [])]
    return dict(video_id=r.get("contentId"), source="lockup", title=meta.get("title", {}).get("content"), channel=rows[0] if rows else None, channel_id=None,
                views_text=next((x for x in rows if x and "view" in x), None), age_text=next((x for x in rows if x and "ago" in x), None), length_text=None)


def parse_results(data):
    """Videos in one search response (first page data or a scroll continuation): list of dicts. Handles `videoRenderer` and the newer
    `lockupViewModel`; Shorts shelves (`reelItemRenderer`, `shortsLockupViewModel`) give an id and a title only (source = 'shorts')."""
    out = []
    for r in _walk(data, "videoRenderer"):
        ch = (r.get("ownerText") or {}).get("runs", [{}])[0]
        out.append(dict(video_id=r.get("videoId"), source="video", title=_text(r.get("title")), channel=ch.get("text"),
                        channel_id=ch.get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId"),
                        views_text=_text(r.get("viewCountText")), age_text=_text(r.get("publishedTimeText")), length_text=_text(r.get("lengthText"))))
    out += [h for h in map(_lockup_video, _walk(data, "lockupViewModel")) if h]
    for r in _walk(data, "reelItemRenderer"):
        out.append(dict(video_id=r.get("videoId"), source="shorts", title=_text(r.get("headline")), channel=None, channel_id=None,
                        views_text=_text(r.get("viewCountText")), age_text=None, length_text=None))
    for r in _walk(data, "shortsLockupViewModel"):
        vid = r.get("onTap", {}).get("innertubeCommand", {}).get("reelWatchEndpoint", {}).get("videoId")
        out.append(dict(video_id=vid, source="shorts", title=r.get("overlayMetadata", {}).get("primaryText", {}).get("content"), channel=None,
                        channel_id=None, views_text=r.get("overlayMetadata", {}).get("secondaryText", {}).get("content"), age_text=None, length_text=None))
    return [o for o in out if o["video_id"]]


def search(br, term, sort="views", max_results=200, idle_scrolls=4):
    """Scroll the search results of `term` until `max_results` videos, or `idle_scrolls` scrolls in a row bring nothing new.
    Returns (results in order, reached_end). The first batch is read from the page, later ones from the page's own responses."""
    batches = []

    def keep(r):
        if "/youtubei/v1/search" in r.url:
            batches.append(r)

    br.page.on("response", keep)
    br.goto(f"https://www.youtube.com/results?search_query={term.replace(' ', '+')}&sp={SORT[sort]}&hl=en")
    br.page.wait_for_selector("ytd-video-renderer, ytd-item-section-renderer", timeout=20000)
    seen, results, idle = set(), [], 0
    first = br.page.evaluate("() => window.ytInitialData")
    while len(results) < max_results and idle < idle_scrolls:
        data = [first] if first else []
        first = None
        for r in batches:
            try:
                data.append(r.json())
            except Exception:
                pass
        batches.clear()
        new = [h for d in data for h in parse_results(d) if h["video_id"] not in seen]
        for h in new:
            seen.add(h["video_id"])
            results.append(h)
        idle = 0 if new else idle + 1
        br.page.mouse.wheel(0, 30000)
        time.sleep(1.5)
        br._check_block()
    br.page.remove_listener("response", keep)
    return results[:max_results], idle >= idle_scrolls


def all_terms(years=True):
    """Every query in the order they are run: core, extended, ambiguous terms, then (if `years`) "<core term> <year>" for 2020 to 2026.
    One query shows at most about 500 videos and search cannot be limited to a past period, so the year queries reach older videos."""
    terms = [t for ts in QUERIES.values() for t in ts]
    return terms + [f"{t} {y}" for t in QUERIES["core"] for y in range(2020, 2027)] if years else terms


def pending_queries(con, terms, sorts, max_results):
    """(term, sort) pairs not done yet: a query counts as done when its results ran out or the cap `max_results` was reached."""
    done = set(con.execute("SELECT term, sort FROM searches WHERE reached_end = 1 OR results >= ?", (max_results,)))
    return [(t, s) for t in terms for s in sorts if (t, s) not in done]


def store_search(con, term, sort, res, end, seconds):
    """Store the videos of one query in `hits` and the run in `searches`."""
    stamp = now()
    con.executemany("INSERT OR IGNORE INTO hits VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(h["video_id"], term, sort, i, stamp, h["source"], h["title"], h["channel_id"], h["channel"], h["views_text"], h["age_text"],
                      h["length_text"]) for i, h in enumerate(res)])
    con.execute("INSERT OR REPLACE INTO searches VALUES (?,?,?,?,?,?)", (term, sort, stamp, len(res), int(end), round(seconds, 1)))
    con.commit()


def search_one(br, con, term, sort, max_results):
    """Run one query and store it; returns (videos shown, reached end of results)."""
    t0 = time.time()
    res, end = search(br, term, sort, max_results)
    store_search(con, term, sort, res, end, time.time() - t0)
    return len(res), end


def run_search(terms=None, sorts=("views", "date"), max_results=500, headless=True, years=False):
    """Run every query not done yet (see `all_terms`); prints one line per query."""
    con = db()
    todo = pending_queries(con, terms or all_terms(years), sorts, max_results)
    with Browser(headless) as br:
        for term, sort in todo:
            n, end = search_one(br, con, term, sort, max_results)
            print(f"search {term!r} by {sort}: {n} videos, reached end of results: {end}")


# ------------------------------------------------------------------ comments
COMMENT_JS = """(skip) => [...document.querySelectorAll('ytd-comment-thread-renderer')].slice(skip).map(t => {
    const q = s => t.querySelector(s), time = q('#published-time-text');
    return {text: q('#content-text')?.innerText ?? '', likes: q('#vote-count-middle')?.innerText?.trim() ?? '', age: time?.innerText?.trim() ?? '',
            replies: q('ytd-comment-replies-renderer #more-replies')?.innerText?.trim() ?? '', pinned: !!q('ytd-pinned-comment-badge-renderer'),
            hearted: !!q('#creator-heart'), edited: (time?.parentElement?.innerText ?? '').includes('edited')}})"""


def read_comments(br, n, sort="top", pause=1.2, idle_scrolls=4):
    """Scroll the comment section of the open watch page until `n` top-level comments are loaded (about 20 per scroll) or `idle_scrolls`
    scrolls bring nothing new; returns dicts (text, likes, age, replies, pinned, hearted, edited) in page order. Authors are never read.
    sort = "top" (YouTube's default, liked comments first) or "newest" (menu entry "Newest"). Only the age as YouTube writes it ("3 years
    ago", rounded down) is available, not a date."""
    if sort == "newest":
        second = "() => document.querySelectorAll('ytd-comment-thread-renderer #content-text')[1]?.innerText ?? ''"      # the first can be a pinned comment in both sorts
        before = br.page.evaluate(second)
        menu = br.page.locator("ytd-comments-header-renderer #sort-menu").first
        menu.scroll_into_view_if_needed(timeout=8000)
        menu.click(timeout=8000)
        br.page.locator("ytd-comments-header-renderer tp-yt-paper-listbox a, ytd-menu-popup-renderer a").filter(has_text="Newest").first.click(timeout=8000)
        try:                                       # wait until the list shows other comments than before
            br.page.wait_for_function("(old) => (document.querySelectorAll('ytd-comment-thread-renderer #content-text')[1]?.innerText ?? '') !== old", arg=before, timeout=8000)
        except Exception:
            pass
        time.sleep(1.5)
    try:
        br.page.wait_for_selector("ytd-comment-thread-renderer", timeout=12000)
    except Exception:
        return []
    have, idle = br.page.locator("ytd-comment-thread-renderer").count(), 0
    while have < n and idle < idle_scrolls:
        br.page.mouse.wheel(0, 4000)
        time.sleep(pause)
        now_count = br.page.locator("ytd-comment-thread-renderer").count()
        idle = 0 if now_count > have else idle + 1
        have = now_count
        br._check_block()
    return br.page.evaluate(COMMENT_JS, 0)[:n]


def fetch_comments(br, video_id, n=200, sorts=("top",)):
    """Open the watch page and read `n` comments in each of `sorts`; returns (status, count text, {sort: comments}). Used by yt_comments."""
    br.goto(f"https://www.youtube.com/watch?v={video_id}&hl=en")
    try:
        br.page.wait_for_function("() => window.ytInitialPlayerResponse", timeout=15000)
    except Exception:
        return "no_player", None, {}
    status = (br.page.evaluate("() => window.ytInitialPlayerResponse").get("playabilityStatus") or {}).get("status", "unknown")
    if status != "OK":
        return status, None, {}
    br.page.mouse.wheel(0, 900)
    try:
        br.page.wait_for_function("() => /\\d/.test(document.querySelector('ytd-comments-header-renderer #count')?.innerText || '')", timeout=12000)
    except Exception:
        return ("comments_off" if "turned off" in (br.page.locator("#comments").first.inner_text() if br.page.locator("#comments").count() else "") else "no_comments"), None, {}
    count = " ".join(br.page.locator("ytd-comments-header-renderer #count").first.inner_text().split())
    return "OK", count, {sort: read_comments(br, n, sort) for sort in sorts}


# ------------------------------------------------------------------ watch page
def slim(player, page, comment_count_text):
    """The parts of a watch page that the dataset uses (the full page is about 1 MB; the stream URLs, ads and storyboards are dropped).
    Nothing is interpreted here: numbers stay as the page writes them."""
    micro = dict(player.get("microformat", {}).get("playerMicroformatRenderer", {}))
    micro["availableCountries"] = len(micro.get("availableCountries", []))
    details = {k: v for k, v in player.get("videoDetails", {}).items() if k != "thumbnail"}
    tracks = player.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    subs = next(iter(_walk(page, "subscriberCountText")), None)
    like = next((x for x in _walk(page, "accessibilityText") if isinstance(x, str) and "like this video" in x), None)
    related = [r.get("contentId") for r in _walk(page, "lockupViewModel") if r.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO"]
    return dict(playability=(player.get("playabilityStatus") or {}).get("status"), details=details,
                micro={k: v for k, v in micro.items() if k not in ("thumbnail", "embed", "title", "description")},
                caption_langs=[t.get("languageCode") for t in tracks], auto_captions=[t.get("kind") == "asr" for t in tracks],
                subscribers_text=(subs or {}).get("accessibility", {}).get("accessibilityData", {}).get("label") or _text(subs),
                like_text=like, comment_count_text=comment_count_text, related=related)


def fetch_watch(br, video_id, n_comments=0):
    """Open the watch page; returns (status, slim dict, comment texts). The comment count and the comments load only after scrolling."""
    br.goto(f"https://www.youtube.com/watch?v={video_id}&hl=en")
    try:
        br.page.wait_for_function("() => window.ytInitialPlayerResponse", timeout=15000)
    except Exception:
        return "no_player", {}, []
    player = br.page.evaluate("() => window.ytInitialPlayerResponse")
    page = br.page.evaluate("() => window.ytInitialData")
    count, comments = None, []
    if (player.get("playabilityStatus") or {}).get("status") == "OK":
        for _ in range(2):                            # the first scroll is sometimes too early
            br.page.mouse.wheel(0, 900)
            try:
                br.page.wait_for_function("() => /\\d/.test(document.querySelector('ytd-comments-header-renderer #count')?.innerText || '')", timeout=8000)
                count = " ".join(br.page.locator("ytd-comments-header-renderer #count").first.inner_text().split())
                break
            except Exception:
                if br.page.locator("#comments").count() and "turned off" in br.page.locator("#comments").first.inner_text():
                    count = "Comments are turned off"
                    break
        if n_comments and count and count[:1].isdigit():
            comments = read_comments(br, n_comments)
    return (player.get("playabilityStatus") or {}).get("status", "unknown"), slim(player, page, count), comments


def store_video(con, vid, status, raw, comments=(), sort="top"):
    """Store one fetched watch page (slim JSON compressed) and its comments (dicts from `read_comments`)."""
    stamp = now()
    con.execute("INSERT OR REPLACE INTO videos VALUES (?,?,?,?,?)", (vid, stamp, PARSER_VERSION, status, zlib.compress(json.dumps(raw).encode())))
    if comments:                                    # a page fetched without comments must not wipe comments stored earlier
        store_comments(con, vid, sort, comments, stamp)
    con.commit()


def store_comments(con, vid, sort, comments, stamp=None):
    """Comments of one video and sort into `comments2` (replaces what was stored for that video and sort)."""
    stamp = stamp or now()
    con.execute("DELETE FROM comments2 WHERE video_id = ? AND sort = ?", (vid, sort))
    con.executemany("INSERT INTO comments2 VALUES (?,?,?,?,?,?,?,?,?,?,?)", [(vid, sort, k, c["text"], c["likes"], c["age"], c["replies"], int(c["pinned"]), int(c["hearted"]), int(c["edited"]), stamp)
                                                                            for k, c in enumerate(comments)])
    con.commit()


def fetch_one(br, con, vid, n_comments=0):
    """Fetch and store one watch page; returns (status, slim dict)."""
    status, raw, comments = fetch_watch(br, vid, n_comments)
    store_video(con, vid, status, raw, comments)
    return status, raw


def unfetched(con, limit=None):
    """Video ids found by search and not fetched yet (with the current parser version), best search rank first."""
    q = """SELECT video_id FROM hits WHERE video_id NOT IN (SELECT video_id FROM videos WHERE parser_version = ?)
           GROUP BY video_id ORDER BY min(rank)""" + (" LIMIT ?" if limit else "")
    return [r[0] for r in con.execute(q, (PARSER_VERSION, limit) if limit else (PARSER_VERSION,))]


def run_detail(limit=300, n_comments=0, headless=True):
    """Fetch the watch page of videos found by `search` and not fetched yet. (`python -m src.yt_run` does search and detail together.)"""
    con = db()
    todo = unfetched(con, limit)
    print(f"{len(todo)} videos to fetch")
    t0 = time.time()
    with Browser(headless) as br:
        for i, vid in enumerate(todo, 1):
            fetch_one(br, con, vid, n_comments)
            if i % 25 == 0:
                print(f"  {i}/{len(todo)}, {(time.time() - t0) / i:.1f} s per video")


def fetch_related(br, video_id, k=10):
    """Open the watch page and return (status, first k recommended videos in sidebar order). A fresh logged-out browser sees the
    recommendations of the video itself, not of a person. Playlists, mixes and Shorts shelves are skipped: only video cards count."""
    br.goto(f"https://www.youtube.com/watch?v={video_id}&hl=en")
    try:
        br.page.wait_for_function("() => window.ytInitialPlayerResponse && window.ytInitialData", timeout=15000)
    except Exception:
        return "no_player", []
    status = (br.page.evaluate("() => window.ytInitialPlayerResponse").get("playabilityStatus") or {}).get("status", "unknown")
    page = br.page.evaluate("() => window.ytInitialData")
    recs = [h for h in map(_lockup_video, _walk(page, "lockupViewModel")) if h and h["video_id"] != video_id]
    return status, recs[:k]


# ------------------------------------------------------------------ several browsers at once
def worker(index, workers, tasks, results, stop, headless):
    """Process body: one Chromium, takes tasks ("search", term, sort, max_results), ("detail", video_id, n_comments), ("related", video_id, k) or ("comments", video_id, n, sorts) from `tasks`, puts
    (task, output, error, seconds) on `results`. Never touches SQLite. A CAPTCHA sets `stop` for everybody. Start times are staggered so
    the workers' page loads are spread evenly over the DELAY."""
    import queue
    time.sleep(index * DELAY / workers)
    with Browser(headless) as br:
        while not stop.is_set():
            try:
                task = tasks.get(timeout=1)
            except queue.Empty:
                continue
            t0 = time.time()
            try:
                out = {"search": search, "detail": fetch_watch, "related": fetch_related, "comments": fetch_comments}[task[0]](br, *task[1:])
                results.put((task, out, None, time.time() - t0))
            except Blocked as e:
                stop.set()
                results.put((task, None, f"blocked: {e}", time.time() - t0))
            except Exception as e:
                results.put((task, None, f"{type(e).__name__}: {e}"[:300], time.time() - t0))


class Pool:
    """`workers` browsers in separate processes. `submit` tasks, `get` results as they finish; only the main process writes to the database."""

    def __init__(self, workers=3, headless=True):
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        self.tasks, self.results, self.stop = ctx.Queue(), ctx.Queue(), ctx.Event()
        self.procs = [ctx.Process(target=worker, args=(i, workers, self.tasks, self.results, self.stop, headless), daemon=True) for i in range(workers)]
        for p in self.procs:
            p.start()

    def submit(self, task):
        self.tasks.put(task)

    def get(self):
        """Next finished (task, output, error, seconds); raises if every worker has died."""
        import queue
        while True:
            try:
                return self.results.get(timeout=5)
            except queue.Empty:
                if not any(p.is_alive() for p in self.procs):
                    raise RuntimeError("all browser workers have stopped")

    def close(self):
        self.stop.set()
        for p in self.procs:
            p.join(timeout=20)
            if p.is_alive():
                p.terminate()


def report():
    con = db()
    print(con.execute("SELECT term, sort, results, reached_end, seconds FROM searches ORDER BY fetched_at").fetchall())
    print("hits:", con.execute("SELECT count(*), count(DISTINCT video_id) FROM hits").fetchone(), "videos fetched:",
          con.execute("SELECT status, count(*) FROM videos GROUP BY status").fetchall())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["search", "detail", "report"])
    ap.add_argument("--terms", nargs="*")
    ap.add_argument("--sorts", nargs="*", default=["views", "date"])
    ap.add_argument("--max-results", type=int, default=500)
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--comments", type=int, default=0, help="top comments (text only, no authors) to store per video")
    ap.add_argument("--years", action="store_true", help="also search '<core term> <year>' for 2020-2026")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    a = ap.parse_args()
    if a.step == "search":
        run_search(a.terms, a.sorts, a.max_results, not a.headed, a.years)
    elif a.step == "detail":
        run_detail(a.limit, a.comments, not a.headed)
    else:
        report()


if __name__ == "__main__":
    main()
