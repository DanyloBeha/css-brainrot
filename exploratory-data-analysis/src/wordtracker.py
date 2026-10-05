# "rizz" whole word only, "brain rot" also matches brain-rot
# trailing * = any ending, regex=True = raw RE2 (slow)
# exact strings only, no synonyms
# track(["doomscroll*"], by="year") or python -m src.wordtracker ...
import argparse
import re

import duckdb
import pandas as pd

from .config import AGG, PROC
from .lexicons import clean_sql


def pattern(term, regex=False):
    if regex:
        return term
    t = term.strip().lower()
    wild = t.endswith("*")
    t = t.rstrip("*")
    return "[ -]+".join(re.escape(p) for p in t.split()) + (r"\w*" if wild else "")


def _q(s):
    return s.replace("'", "''")


def track(terms, by="month", types=("comment",), subreddits=None, regex=False, pool=False, min_tokens=50_000):
    # pool=True sums hits and words, big samples weigh more
    groups = terms if isinstance(terms, dict) else {t: [t] for t in terms}
    names = list(groups)
    pats = {n: r"\b(" + "|".join(pattern(t, regex) for t in groups[n]) + r")\b" for n in names}
    roots = [] if regex else [t.strip().lower().rstrip("*").split()[0] for n in names for t in groups[n]]
    pre = " OR ".join(f"contains(lower(text), '{_q(r)}')" for r in roots) or "TRUE"
    cols = ", ".join(f"len(regexp_extract_all(clean, '{_q(pats[n])}', 1)) AS h{i}" for i, n in enumerate(names))
    agg = ", ".join(f"sum(h{i}) AS hits_{i}, sum((h{i} > 0)::INT) AS rows_{i}" for i in range(len(names)))
    tlist = ", ".join(f"'{t}'" for t in types)
    sub = f"AND subreddit IN ({', '.join(repr(s) for s in subreddits)})" if subreddits else ""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    hits = con.execute(f"""
        WITH cand AS (SELECT type, subreddit, date_trunc('month', ts) AS month, {clean_sql('text')} AS clean
                      FROM read_parquet('{PROC}/*.parquet') WHERE type IN ({tlist}) {sub} AND ({pre})),
        m AS (SELECT type, subreddit, month, {cols} FROM cand)
        SELECT type, subreddit, month, {agg} FROM m GROUP BY ALL""").df()
    base = pd.read_parquet(AGG / "overview_counts.parquet")[["type", "subreddit", "month", "rows", "tokens"]]
    base = base[base.type.isin(types)]
    if subreddits:
        base = base[base.subreddit.isin(subreddits)]
    out = []
    for i, n in enumerate(names):
        h = hits[["type", "subreddit", "month", f"hits_{i}", f"rows_{i}"]].rename(columns={f"hits_{i}": "hits", f"rows_{i}": "rows_with_hit"})
        d = base.merge(h, on=["type", "subreddit", "month"], how="left").fillna({"hits": 0, "rows_with_hit": 0})
        out.append(d.assign(name=n))
    df = pd.concat(out, ignore_index=True).rename(columns={"tokens": "words"})
    df["period"] = df["month"].dt.to_period("Y").dt.to_timestamp() if by == "year" else df["month"]
    keys = ["name", "type", "period"] + ([] if pool else ["subreddit"])
    df = df.groupby(keys, as_index=False)[["hits", "rows_with_hit", "words", "rows"]].sum()
    if pool:
        df["subreddit"] = "all"
    df = df[df.words >= min_tokens]
    df["per_10k_words"] = df.hits * 1e4 / df.words
    df["reach"] = df.rows_with_hit / df.rows
    return df[["name", "type", "subreddit", "period", "hits", "rows_with_hit", "words", "rows", "per_10k_words", "reach"]]


def main():
    ap = argparse.ArgumentParser(description="Rate per 10,000 words of words or phrases in the cleaned Reddit comments (see module docstring).")
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--by", choices=["month", "year"], default="year")
    ap.add_argument("--types", nargs="+", default=["comment"])
    ap.add_argument("--subreddits", nargs="+")
    ap.add_argument("--regex", action="store_true")
    a = ap.parse_args()
    df = track(a.terms, by=a.by, types=tuple(a.types), subreddits=a.subreddits, regex=a.regex, pool=True)
    pd.set_option("display.width", 200)
    print("hits per 10,000 words, all selected subreddits pooled\n")
    print(df.pivot_table(index="period", columns="name", values="per_10k_words").round(3).to_string())
    print("\nraw hits\n")
    print(df.pivot_table(index="period", columns="name", values="hits").astype(int).to_string())


if __name__ == "__main__":
    main()
