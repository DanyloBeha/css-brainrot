"""Raw Arctic Shift Parquet -> one common-schema Parquet file per type and subreddit.

Common schema (comments and submissions share it, so one table serves group-level
and event-level views; analyses still filter on `type`):

    id, type, author_id, ts (UTC), subreddit, text, score, link_id, num_comments,
    slot_start, n_tokens

* comments:    text = body
* submissions: text = title + "\\n" + selftext (selftext dropped when empty or removed);
               link_id = "t3_" + id so comments can be joined to their submission.
* author_id is a 12-char md5 hash; NULL when the account was deleted (the text is kept,
  so text metrics do not lose ~10% of rows, but author-level analyses skip them).
* slot_start is the start of the time slot the sample was drawn from (needed for
  sessionization, because only whole slots were downloaded).
* n_tokens counts tokens with the shared tokenizer in lexicons.py.

Cleaning rules (in this order, each row counted once): bot accounts; moderator/admin-distinguished
comments (official moderation messages); templated text (first 100 characters seen >= 300 times in
the whole archive: removal notices, rule reminders, link bots); empty or removed text; spam
(>= 100 words with fewer than 15% distinct words); duplicate ids.
"""
import time

import duckdb
import polars as pl

from .config import AGG, PROC, RAW
from .lexicons import TOKEN_RE_SQL, clean_sql, n_tokens_sql

KINDS = {"comments": "comment", "submissions": "submission"}
BOT_SQL = "author = 'AutoModerator' OR lower(author) LIKE '%bot'"
TEMPLATE_MIN_COPIES = 300
SPAM_MIN_WORDS, SPAM_MAX_DISTINCT = 100, 0.15


def _text_sql(kind):
    if kind == "comments":
        return "body"
    return ("trim(coalesce(title, '')) || CASE WHEN selftext IS NULL OR "
            "trim(selftext) IN ('', '[removed]', '[deleted]') THEN '' "
            "ELSE chr(10) || selftext END")


def _dist_sql(kind):
    return "distinguished" if kind == "comments" else "CAST(NULL AS VARCHAR) AS distinguished"


def make_templates(con):
    """Texts (first 100 characters) that occur at least TEMPLATE_MIN_COPIES times among comments."""
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE templates AS
        SELECT left(body, 100) AS t FROM read_parquet('{RAW / "comments"}/*/*/*.parquet', hive_partitioning=false)
        WHERE length(body) >= 40 GROUP BY 1 HAVING count(*) >= {TEMPLATE_MIN_COPIES}""")
    return con.execute("SELECT count(*) FROM templates").fetchone()[0]


def _extra_sql(kind):
    if kind == "comments":
        return "link_id, CAST(NULL AS BIGINT) AS num_comments"
    return "'t3_' || id AS link_id, num_comments"


def build_one(con, kind, subreddit):
    """Convert one (kind, subreddit). Returns the drop-reason counts as a dict."""
    src = RAW / kind / f"subreddit={subreddit}" / "year=*" / "*.parquet"
    out = PROC / f"{KINDS[kind]}_{subreddit}.parquet"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE flagged AS
        WITH r AS (
          SELECT id, author, created_utc, score, lower(subreddit) AS subreddit, slot_start, {_dist_sql(kind)},
                 {_extra_sql(kind)}, {_text_sql(kind)} AS text
          FROM read_parquet('{src}', hive_partitioning=false)),
        t AS (
          SELECT *, CASE WHEN length(text) >= 400
                         THEN regexp_extract_all({clean_sql('text')}, '{TOKEN_RE_SQL}') END AS toks FROM r)
        SELECT id, author, created_utc, score, subreddit, slot_start, link_id, num_comments, text,
               CASE WHEN author IS NOT NULL AND ({BOT_SQL}) THEN 'bot'
                    WHEN distinguished IN ('moderator', 'admin') THEN 'moderator'
                    WHEN left(text, 100) IN (SELECT t FROM templates) AND length(text) >= 40 AND {'TRUE' if kind == 'comments' else 'FALSE'} THEN 'template'
                    WHEN trim(coalesce(text, '')) IN ('', '[removed]', '[deleted]') THEN 'empty_or_removed'
                    WHEN toks IS NOT NULL AND len(toks) >= {SPAM_MIN_WORDS}
                         AND len(list_distinct(toks)) < {SPAM_MAX_DISTINCT} * len(toks) THEN 'spam'
                    ELSE 'keep' END AS reason
        FROM t""")
    counts = dict(con.execute("SELECT reason, count(*) FROM flagged GROUP BY 1").fetchall())
    raw_n = sum(counts.values())
    kept = counts.get("keep", 0)
    deleted_author = con.execute(
        "SELECT count(*) FROM flagged WHERE reason = 'keep' AND (author IS NULL OR author = '[deleted]')"
    ).fetchone()[0]
    con.execute(f"""
        COPY (
          SELECT id, '{KINDS[kind]}' AS type,
                 CASE WHEN author IS NULL OR author = '[deleted]' THEN NULL
                      ELSE left(md5(author), 12) END AS author_id,
                 make_timestamp(created_utc * 1000000) AS ts,     -- naive UTC
                 subreddit, text, score, link_id, num_comments, slot_start,
                 {n_tokens_sql('text')} AS n_tokens
          FROM flagged WHERE reason = 'keep'
          QUALIFY row_number() OVER (PARTITION BY id ORDER BY created_utc) = 1
        ) TO '{out}' (FORMAT parquet, COMPRESSION zstd)""")
    final = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    rec = {"type": KINDS[kind], "subreddit": subreddit, "raw_rows": raw_n,
           "dropped_bot": counts.get("bot", 0),
           "dropped_moderator": counts.get("moderator", 0),
           "dropped_template": counts.get("template", 0),
           "dropped_empty_or_removed": counts.get("empty_or_removed", 0),
           "dropped_spam": counts.get("spam", 0),
           "dropped_duplicate_id": kept - final, "final_rows": final,
           "kept_with_deleted_author": deleted_author}
    assert rec["raw_rows"] == (rec["dropped_bot"] + rec["dropped_moderator"] + rec["dropped_template"]
                               + rec["dropped_empty_or_removed"] + rec["dropped_spam"]
                               + rec["dropped_duplicate_id"] + rec["final_rows"]), rec
    return rec


def build_all():
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    print(f"{make_templates(con)} templated texts found")
    rows = []
    for kind in KINDS:
        for d in sorted((RAW / kind).glob("subreddit=*")):
            sub = d.name.split("=", 1)[1]
            t0 = time.time()
            rec = build_one(con, kind, sub)
            rows.append(rec)
            print(f"{rec['type']:<10} {sub:<18} raw {rec['raw_rows']:>9,} "
                  f"-bots {rec['dropped_bot']:>7,} -mod {rec['dropped_moderator']:>7,} -tmpl {rec['dropped_template']:>6,} "
                  f"-empty {rec['dropped_empty_or_removed']:>8,} -spam {rec['dropped_spam']:>5,} "
                  f"-dupes {rec['dropped_duplicate_id']:>3,} = {rec['final_rows']:>9,} "
                  f"({time.time() - t0:.0f}s)")
    counts = pl.DataFrame(rows)
    counts.write_parquet(AGG / "cleaning_counts.parquet")
    return counts
