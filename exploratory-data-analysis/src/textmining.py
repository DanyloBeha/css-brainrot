"""Lexicon matches and monthly rates (Phase 3). Row-level matches stay in data/processed (local)."""
import time

import duckdb
import pandas as pd

from .config import AGG, PROC
from .lexicons import (BRAINROT_CORE_RE, BRAINROT_EXT_RE, DOOM_RE, PREFILTER, SIGMA_RE, clean_sql)

MATCHES = PROC / "derived" / "lexicon_matches.parquet"      # sub-folder: the row-level globs *.parquet in PROC must not see it
TIERS = {"core": "core_terms", "extended": "ext_terms", "sigma": "sigma_terms", "doom": "doom_terms"}


def _con():
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con


def build_matches():
    """One pass over all text: keep the rows that contain any lexicon term, with the matched strings per tier."""
    MATCHES.parent.mkdir(exist_ok=True)
    con = _con()
    t0 = time.time()
    con.execute(f"""
        COPY (
          WITH cand AS (
            SELECT id, type, subreddit, ts, author_id, n_tokens, text, {clean_sql('text')} AS clean
            FROM read_parquet('{PROC}/comment_*.parquet') WHERE regexp_matches(lower(text), '{PREFILTER}')
            UNION ALL
            SELECT id, type, subreddit, ts, author_id, n_tokens, text, {clean_sql('text')} AS clean
            FROM read_parquet('{PROC}/submission_*.parquet') WHERE regexp_matches(lower(text), '{PREFILTER}')
          ), m AS (
            SELECT *, regexp_extract_all(clean, '{BRAINROT_CORE_RE}', 1) AS core_terms,
                   regexp_extract_all(clean, '{BRAINROT_EXT_RE}', 1) AS ext_terms,
                   regexp_extract_all(clean, '{SIGMA_RE}', 1) AS sigma_terms,
                   regexp_extract_all(clean, '{DOOM_RE}', 1) AS doom_terms
            FROM cand)
          SELECT id, type, subreddit, ts, author_id, n_tokens, text, core_terms, ext_terms, sigma_terms, doom_terms
          FROM m WHERE len(core_terms) + len(ext_terms) + len(sigma_terms) + len(doom_terms) > 0
        ) TO '{MATCHES}' (FORMAT parquet, COMPRESSION zstd)""")
    n = con.execute(f"SELECT count(*) FROM read_parquet('{MATCHES}')").fetchone()[0]
    print(f"{n:,} rows with a lexicon match ({time.time() - t0:.0f}s)")
    return n


def lexicon_monthly(min_tokens=50_000):
    """Hits per 10,000 words and reach (share of rows with a hit), per tier x type x subreddit x month."""
    con = _con()
    hits = con.execute(f"""
        SELECT type, subreddit, date_trunc('month', ts) AS month, tier,
               sum(n) AS hits, count(*) AS rows_with_hit
        FROM (
          SELECT type, subreddit, ts, 'core' AS tier, len(core_terms) AS n FROM read_parquet('{MATCHES}') WHERE len(core_terms) > 0
          UNION ALL SELECT type, subreddit, ts, 'extended', len(ext_terms) FROM read_parquet('{MATCHES}') WHERE len(ext_terms) > 0
          UNION ALL SELECT type, subreddit, ts, 'sigma', len(sigma_terms) FROM read_parquet('{MATCHES}') WHERE len(sigma_terms) > 0
          UNION ALL SELECT type, subreddit, ts, 'doom', len(doom_terms) FROM read_parquet('{MATCHES}') WHERE len(doom_terms) > 0
        ) GROUP BY ALL""").df()
    base = pd.read_parquet(AGG / "overview_counts.parquet")[["type", "subreddit", "month", "rows", "tokens"]]
    grid = base.assign(key=1).merge(pd.DataFrame({"tier": list(TIERS), "key": 1}), on="key").drop(columns="key")
    df = grid.merge(hits, on=["type", "subreddit", "month", "tier"], how="left").fillna({"hits": 0, "rows_with_hit": 0})
    df["per_10k_words"] = df["hits"] * 10_000 / df["tokens"]
    df["reach"] = df["rows_with_hit"] / df["rows"]
    df["enough_tokens"] = df["tokens"] >= min_tokens
    df.to_parquet(AGG / "lexicon_monthly.parquet", index=False)
    print(f"lexicon_monthly: {len(df):,} rows")
    return df


def term_counts():
    """How often each individual term occurs: per day (lexicon_terms_daily, event-time charts), per month (lexicon_terms_by_month,
    stream graphs) and per year (lexicon_terms_by_year, checks)."""
    con = _con()
    d = con.execute(f"""
        SELECT CAST(ts AS DATE) AS day, type, subreddit, tier, lower(term) AS term, count(*) AS n
        FROM (
          SELECT ts, type, subreddit, 'core' AS tier, unnest(core_terms) AS term FROM read_parquet('{MATCHES}')
          UNION ALL SELECT ts, type, subreddit, 'extended', unnest(ext_terms) FROM read_parquet('{MATCHES}')
          UNION ALL SELECT ts, type, subreddit, 'sigma', unnest(sigma_terms) FROM read_parquet('{MATCHES}')
          UNION ALL SELECT ts, type, subreddit, 'doom', unnest(doom_terms) FROM read_parquet('{MATCHES}')
        ) GROUP BY ALL ORDER BY ALL""").df()
    d["day"] = pd.to_datetime(d["day"])
    d.to_parquet(AGG / "lexicon_terms_daily.parquet", index=False)
    keys = ["type", "subreddit", "tier", "term"]
    m = d.assign(month=d["day"].dt.to_period("M").dt.to_timestamp()).groupby(["month"] + keys, as_index=False)["n"].sum()
    m.to_parquet(AGG / "lexicon_terms_by_month.parquet", index=False)
    yr = d.assign(year=d["day"].dt.year).groupby(["year"] + keys, as_index=False)["n"].sum()
    yr.to_parquet(AGG / "lexicon_terms_by_year.parquet", index=False)
    print(f"lexicon_terms_daily: {len(d):,} rows; by_month: {len(m):,}; by_year: {len(yr):,}")
    return d


# ------------------------------------------------------------------ emoji
EMOJI_RE = r"[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B50}\x{2B55}]"      # emoticon, symbol and pictograph blocks


def emoji_monthly():
    """Emoji code points per 10,000 words by type x subreddit x month (approximation: no ZWJ/flag merging)."""
    con = _con()
    df = con.execute(f"""
        SELECT type, subreddit, date_trunc('month', ts) AS month,
               sum(len(regexp_extract_all(text, '{EMOJI_RE}'))) AS emoji, sum(n_tokens) AS tokens,
               avg((regexp_matches(text, '{EMOJI_RE}'))::INT) AS reach
        FROM read_parquet('{PROC}/*.parquet') GROUP BY ALL ORDER BY ALL""").df()
    df["per_10k_words"] = df["emoji"] * 10_000 / df["tokens"]
    df.to_parquet(AGG / "emoji_monthly.parquet", index=False)
    print(f"emoji_monthly: {len(df):,} rows")
    return df


# ------------------------------------------------------------------ MTLD, readability, sentiment
MTLD_TOKENS, VADER_N, FLESCH_N = 5000, 2000, 400
URL = r"https?://\S+|www\.\S+"


def _cell_metrics(args):
    """Metrics for one subreddit-month. `rows` = DataFrame sorted by random rank."""
    import re

    import numpy as np
    import textstat
    from lexicalrichness import LexicalRichness
    from nltk.sentiment import SentimentIntensityAnalyzer
    sub, month, texts, ntok = args
    clean = [re.sub(URL, " ", t) for t in texts]
    out = {"subreddit": sub, "month": month}
    # MTLD on the first random comments that add up to a fixed number of tokens
    cum = np.cumsum(ntok)
    k = int(np.searchsorted(cum, MTLD_TOKENS)) + 1
    if cum[-1] >= MTLD_TOKENS:
        out["mtld"] = LexicalRichness(" ".join(clean[:k])).mtld(threshold=0.72)
        out["mtld_words"] = int(cum[min(k, len(cum)) - 1])
    # readability on comments with at least 10 tokens
    long_ = [c for c, n in zip(clean[:FLESCH_N * 3], ntok[:FLESCH_N * 3]) if n >= 10][:FLESCH_N]
    if len(long_) >= 30:
        out["flesch_median"] = float(np.median([textstat.flesch_reading_ease(c) for c in long_]))
        out["flesch_n"] = len(long_)
    sia = SentimentIntensityAnalyzer()
    comp = np.array([sia.polarity_scores(t)["compound"] for t in texts[:VADER_N]])
    out.update(vader_mean=float(comp.mean()), vader_neg_share=float((comp <= -0.05).mean()),
               vader_pos_share=float((comp >= 0.05).mean()), vader_n=len(comp))
    return out


def text_metrics_monthly(workers=6):
    """MTLD (fixed 5,000-token random samples), Flesch (median of up to 400 comments) and VADER (up to 2,000 comments)."""
    from concurrent.futures import ProcessPoolExecutor
    con = _con()
    t0 = time.time()
    df = con.execute(f"""
        SELECT subreddit, month, text, n_tokens FROM (
          SELECT subreddit, date_trunc('month', ts) AS month, text, n_tokens,
                 row_number() OVER w AS rk
          FROM read_parquet('{PROC}/comment_*.parquet')
          WINDOW w AS (PARTITION BY subreddit, date_trunc('month', ts) ORDER BY hash(id || '42'))
        ) WHERE rk <= {VADER_N} ORDER BY subreddit, month, rk""").df()
    print(f"sampled {len(df):,} comments ({time.time() - t0:.0f}s)")
    jobs = [(s, m, g["text"].tolist(), g["n_tokens"].to_numpy()) for (s, m), g in df.groupby(["subreddit", "month"], sort=True)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_cell_metrics, jobs, chunksize=8))
    out = pd.DataFrame(res)
    out.to_parquet(AGG / "text_metrics_monthly.parquet", index=False)
    print(f"text_metrics_monthly: {len(out):,} rows ({time.time() - t0:.0f}s)")
    return out


# ------------------------------------------------------------------ words and bigrams: early vs late
PERIODS = {"early": ("2013-01-01", "2017-01-01"), "late": ("2023-01-01", "2026-10-01")}
GROUP_SUBS = {"short_form": ["memes", "teenagers"], "long_form": ["books", "explainlikeimfive"]}
ARTIFACTS = ("amp", "gt", "lt", "x200b", "nbsp", "deleted", "removed", "giphy", "emote", "img", "gif")           # markdown / export leftovers


def _stop_sql():
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    words = sorted(set(ENGLISH_STOP_WORDS) | set(ARTIFACTS) | {"im", "dont", "ive", "didnt", "thats", "doesnt", "cant", "youre", "isnt"})
    return "[" + ", ".join("'" + w.replace("'", "''") + "'" for w in words) + "]"


def words_period():
    """Word counts per group x period (comments), and the same for bigrams on a fixed random sample."""
    from .lexicons import TOKEN_RE_SQL
    con = _con()
    rows, bi = [], []
    for g, subs in GROUP_SUBS.items():
        sublist = ", ".join(f"'{s}'" for s in subs)
        for per, (a, b) in PERIODS.items():
            base = f"""SELECT id, {clean_sql('text')} AS clean FROM read_parquet('{PROC}/comment_*.parquet')
                       WHERE subreddit IN ({sublist}) AND ts >= '{a}' AND ts < '{b}'"""
            w = con.execute(f"""
                SELECT '{g}' AS grp, '{per}' AS period, word, count(*) AS n FROM (
                  SELECT unnest(regexp_extract_all(clean, '{TOKEN_RE_SQL}')) AS word FROM ({base})
                ) WHERE length(word) > 1 AND word NOT IN ({", ".join(repr(a) for a in ARTIFACTS)}) GROUP BY ALL HAVING count(*) >= 5""").df()
            rows.append(w)
            stop = _stop_sql()
            bg = con.execute(f"""
                WITH s AS (SELECT clean FROM ({base}) ORDER BY hash(id || '7') LIMIT 400000),
                t AS (SELECT regexp_extract_all(clean, '{TOKEN_RE_SQL}') AS toks FROM s),
                b AS (SELECT unnest(list_transform(range(1, len(toks)), i -> [toks[i], toks[i + 1]])) AS pair FROM t WHERE len(toks) >= 2)
                SELECT '{g}' AS grp, '{per}' AS period, pair[1] || ' ' || pair[2] AS bigram, count(*) AS n
                FROM b WHERE NOT list_contains({stop}, pair[1]) AND NOT list_contains({stop}, pair[2])
                  AND length(pair[1]) > 1 AND length(pair[2]) > 1
                GROUP BY ALL HAVING count(*) >= 5""").df()
            bi.append(bg)
            print(g, per, f"{len(w):,} words, {len(bg):,} bigrams")
    pd.concat(rows).to_parquet(AGG / "word_counts_period.parquet", index=False)
    pd.concat(bi).to_parquet(AGG / "bigram_counts_period.parquet", index=False)


# ------------------------------------------------------------------ per-comment features for H4
FEATURES = PROC / "derived"


def _vader_chunk(texts):
    from nltk.sentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    return [sia.polarity_scores(t)["compound"] for t in texts]


def build_features(workers=6, chunk=40_000):
    """Per comment: VADER compound, hits of the crisis lexicon, hits per event lexicon, doomscroll hits.
    One Parquet file per subreddit in data/processed/derived/ (row-level, local)."""
    from concurrent.futures import ProcessPoolExecutor

    from .lexicons import CRISIS_RE, EVENT_RE
    con = _con()
    t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for f in sorted(PROC.glob("comment_*.parquet")):
            sub = f.stem.split("_", 1)[1]
            hits = ", ".join(f"len(regexp_extract_all(clean, '{rx}', 1)) AS hits_{k}" for k, rx in EVENT_RE.items())
            df = con.execute(f"""
                WITH c AS (SELECT id, subreddit, ts, slot_start, n_tokens, text, {clean_sql('text')} AS clean FROM read_parquet('{f}'))
                SELECT id, subreddit, ts, slot_start, n_tokens, text,
                       len(regexp_extract_all(clean, '{CRISIS_RE}', 1)) AS hits_crisis, {hits},
                       len(regexp_extract_all(clean, '{DOOM_RE}', 1)) AS hits_doom
                FROM c""").df()
            texts = df.pop("text").tolist()
            parts = [texts[i:i + chunk] for i in range(0, len(texts), chunk)]
            df["compound"] = [v for part in ex.map(_vader_chunk, parts) for v in part]
            df.to_parquet(FEATURES / f"features_{sub}.parquet", index=False)
            print(f"{sub}: {len(df):,} comments ({time.time() - t0:.0f}s)")
