# sample only, pool months weighted total / sampled rows
import json

import duckdb
import pandas as pd

from .config import AGG, PROC, RAW

TYPES = {"comment": "comments_total", "submission": "posts_total"}


def _con():
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con


def _write(df, name):
    df.to_parquet(AGG / f"{name}.parquet", index=False)
    print(f"{name}: {len(df):,} rows")
    return df


def monthly_totals():
    t = pd.read_csv(RAW / "_monthly_totals.csv")
    t["month"] = pd.to_datetime(t["month"] + "-01")
    long = t.melt(id_vars=["subreddit", "month"], value_vars=list(TYPES.values()),
                  var_name="type", value_name="total")
    long["type"] = long["type"].map({v: k for k, v in TYPES.items()})
    return _write(long, "monthly_totals")


def sample_weights():
    con = _con()
    raw = []
    for kind, typ in (("comments", "comment"), ("submissions", "submission")):
        df = con.execute(f"""
            SELECT subreddit, date_trunc('month', make_timestamp(created_utc * 1000000)) AS month,
                   count(*) AS raw_rows, count(DISTINCT slot_start) AS n_slots
            FROM read_parquet('{RAW / kind}/*/*/*.parquet', hive_partitioning=false)
            GROUP BY ALL""").df()
        df["type"] = typ
        raw.append(df)
    raw = pd.concat(raw)
    raw["month"] = pd.to_datetime(raw["month"]).dt.tz_localize(None)
    tot = pd.read_parquet(AGG / "monthly_totals.parquet")
    w = tot.merge(raw, on=["subreddit", "month", "type"], how="left")
    w["raw_rows"] = w["raw_rows"].fillna(0)
    w["coverage"] = (w["raw_rows"] / w["total"]).clip(upper=1)
    w["weight"] = (w["total"] / w["raw_rows"]).where(w["raw_rows"] > 0).clip(lower=1)
    # slot minutes from sampling plan
    plans = {}
    for fn, typ in (("_sample_plan.json", "comment"), ("_sample_plan_posts.json", "submission")):
        for k, v in json.load(open(RAW / fn))["subreddit_months"].items():
            sub, m = k.split("|")
            plans[(sub, pd.Timestamp(m + "-01"), typ)] = v.get("slot_minutes")
    w["slot_minutes"] = [plans.get((s, m, t)) for s, m, t in zip(w.subreddit, w.month, w.type)]
    return _write(w, "sample_weights")


def overview_counts():
    con = _con()
    df = con.execute(f"""
        SELECT type, subreddit, date_trunc('month', ts) AS month,
               count(*) AS rows,
               count(DISTINCT author_id) AS authors,
               sum(n_tokens) AS tokens,
               median(n_tokens) AS median_tokens,
               avg(n_tokens) AS mean_tokens,
               avg((n_tokens <= 5)::INT) AS short_share,
               avg((author_id IS NULL)::INT) AS deleted_author_share,
               avg(score) AS mean_score
        FROM read_parquet('{PROC}/*.parquet') GROUP BY ALL ORDER BY ALL""").df()
    w = pd.read_parquet(AGG / "sample_weights.parquet")[["type", "subreddit", "month", "total", "weight"]]
    df = df.merge(w, on=["type", "subreddit", "month"], how="left")
    return _write(df, "overview_counts")


def _weighted_hist(group_cols, value_sql, name, where=""):
    con = _con()
    w = AGG / "sample_weights.parquet"
    cols = ", ".join(group_cols)
    df = con.execute(f"""
        SELECT {cols}, {value_sql} AS value, count(*) AS rows, sum(w.weight) AS est_rows
        FROM read_parquet('{PROC}/*.parquet') p
        JOIN read_parquet('{w}') w
          ON w.type = p.type AND w.subreddit = p.subreddit AND w.month = date_trunc('month', p.ts)
        {where}
        GROUP BY ALL ORDER BY ALL""").df()
    return _write(df, name)


def length_hist():
    return _weighted_hist(["p.type AS type", "p.subreddit AS subreddit", "year(p.ts) AS year"],
                          "least(p.n_tokens, 3000)", "length_hist")


def score_hist():
    return _weighted_hist(["p.type AS type", "p.subreddit AS subreddit"],
                          "greatest(least(p.score, 100000), -100)", "score_hist")


def score_by_length():
    con = _con()
    w = AGG / "sample_weights.parquet"
    df = con.execute(f"""
        SELECT p.type AS type, p.subreddit AS subreddit, floor(log2(p.n_tokens + 1))::INT AS len_bin,
               count(*) AS rows, sum(w.weight) AS est_rows,
               sum(w.weight * (p.score >= 10)::INT) AS est_ge10,
               sum(w.weight * (p.score <= 0)::INT) AS est_le0
        FROM read_parquet('{PROC}/*.parquet') p
        JOIN read_parquet('{w}') w
          ON w.type = p.type AND w.subreddit = p.subreddit AND w.month = date_trunc('month', p.ts)
        GROUP BY ALL ORDER BY ALL""").df()
    return _write(df, "score_by_length")


def hour_dow():
    # utc, 1=mon
    return _weighted_hist(
        ["p.type AS type", "p.subreddit AS subreddit", "year(p.ts) AS year",
         "isodow(p.ts) AS dow", "hour(p.ts) AS hour"], "1", "hour_dow")


def author_activity():
    # counted inside sample only
    con = _con()
    df = con.execute(f"""
        WITH per_author AS (
          SELECT subreddit, author_id, count(*) AS msgs
          FROM read_parquet('{PROC}/*.parquet') WHERE author_id IS NOT NULL GROUP BY ALL)
        SELECT subreddit, msgs, count(*) AS authors FROM per_author GROUP BY ALL ORDER BY ALL""").df()
    return _write(df, "author_activity")


def daily_full_coverage(min_coverage=0.9):
    # near-full coverage months only
    con = _con()
    w = AGG / "sample_weights.parquet"
    df = con.execute(f"""
        SELECT p.type AS type, p.subreddit AS subreddit, CAST(date_trunc('day', p.ts) AS DATE) AS day,
               count(*) AS rows
        FROM read_parquet('{PROC}/*.parquet') p
        JOIN read_parquet('{w}') w
          ON w.type = p.type AND w.subreddit = p.subreddit AND w.month = date_trunc('month', p.ts)
        WHERE w.coverage >= {min_coverage}
        GROUP BY ALL ORDER BY ALL""").df()
    return _write(df, "daily_full_coverage")


def build_phase2():
    monthly_totals()
    sample_weights()
    overview_counts()
    length_hist()
    score_hist()
    score_by_length()
    hour_dow()
    author_activity()
    daily_full_coverage()


def raw_quality_monthly():
    from .io_reddit import BOT_SQL
    con = _con()
    parts = []
    for kind, typ, text in (("comments", "comment", "body"), ("submissions", "submission", "title")):
        parts.append(con.execute(f"""
            SELECT '{typ}' AS type, lower(subreddit) AS subreddit,
                   date_trunc('month', make_timestamp(created_utc * 1000000)) AS month,
                   count(*) AS raw_rows,
                   sum((author IS NOT NULL AND ({BOT_SQL}))::INT) AS bot_rows,
                   sum((author = '[deleted]')::INT) AS deleted_author_rows,
                   sum((trim(coalesce({text}, '')) IN ('', '[removed]', '[deleted]'))::INT) AS removed_rows
            FROM read_parquet('{RAW / kind}/*/*/*.parquet', hive_partitioning=false)
            GROUP BY ALL ORDER BY ALL""").df())
    return _write(pd.concat(parts), "raw_quality_monthly")
