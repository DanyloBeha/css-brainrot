"""Checks on the processed Parquet: schema (pandera), reconciliation with raw, missingness."""
import duckdb
import pandera.pandas as pa

from .config import AGG, PROC

SCHEMA = pa.DataFrameSchema({
    "id": pa.Column(str, nullable=False, unique=True),
    "type": pa.Column(str, pa.Check.isin(["comment", "submission"])),
    "author_id": pa.Column(str, pa.Check.str_length(12, 12), nullable=True),
    "ts": pa.Column("datetime64[us]", pa.Check.in_range("2012-01-01", "2026-12-31")),
    "subreddit": pa.Column(str, pa.Check.str_matches(r"^[a-z0-9_]+$")),
    "text": pa.Column(str, pa.Check(lambda s: s.str.strip().ne(""), element_wise=False)),
    "score": pa.Column("Int64", nullable=True),
    "link_id": pa.Column(str, nullable=True),
    "num_comments": pa.Column("Int64", nullable=True),
    "slot_start": pa.Column("Int64", nullable=True),
    "n_tokens": pa.Column("Int64", pa.Check.ge(0)),
}, strict=True)


def sample(n=200_000, seed=42):
    """Random sample of processed rows (reproducible)."""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    return con.execute(
        f"SELECT * FROM read_parquet('{PROC}/*.parquet') USING SAMPLE {n} ROWS (reservoir, {seed})"
    ).df()


def reconcile():
    """Processed row counts = raw rows minus logged drops, per type and subreddit."""
    con = duckdb.connect()
    log = con.execute(f"SELECT * FROM read_parquet('{AGG / 'cleaning_counts.parquet'}')").df()
    real = con.execute(
        f"SELECT type, subreddit, count(*) AS n FROM read_parquet('{PROC}/*.parquet') GROUP BY ALL"
    ).df()
    m = log.merge(real, on=["type", "subreddit"])
    m["ok"] = m["final_rows"] == m["n"]
    return m


def missingness_figure():
    """V01: missingno matrix of a random sample of processed rows (text column left out). Missing values are by design:
    author_id is empty for deleted accounts, num_comments only exists for submissions."""
    import matplotlib
    import missingno as msno

    from .config import FIG
    df = sample().drop(columns=["text"]).sort_values("ts")
    ax = msno.matrix(df, sparkline=False, figsize=(9, 4), fontsize=10, color=(0.35, 0.55, 0.45))
    ax.figure.savefig(FIG / "V01_missingness.png", dpi=150, bbox_inches="tight")
    matplotlib.pyplot.close(ax.figure)
    return df.isna().mean().round(3)


def vader_label_sample(n=100, path=None):
    """100 random comments (8-120 words) with their VADER score and an empty `human_label` column for hand labeling.
    Row-level text: written to data/processed/derived/ (not committed)."""
    from nltk.sentiment import SentimentIntensityAnalyzer
    con = duckdb.connect()
    df = con.execute(f"""SELECT id, subreddit, year(ts) AS year, text FROM read_parquet('{PROC}/comment_*.parquet')
                         WHERE n_tokens BETWEEN 8 AND 120 ORDER BY hash(id || 'vader') LIMIT {n}""").df()
    sia = SentimentIntensityAnalyzer()
    df["vader_compound"] = [sia.polarity_scores(t)["compound"] for t in df.text]
    df["human_label"] = ""                                   # fill with: pos / neg / neutral
    path = path or PROC / "derived" / "vader_validation_sample.csv"
    df.to_csv(path, index=False)
    return path
