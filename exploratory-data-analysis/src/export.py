"""Compact analysis-ready table for the CSV deliverable: one row per subreddit-month, no empty cells."""
import pandas as pd

from .config import AGG, OUT, SUB2GROUP
from . import events as ev


def build_csv(path=None, min_tokens=50_000):
    o = pd.read_parquet(AGG / "overview_counts.parquet")
    c = o[o.type == "comment"][["subreddit", "month", "rows", "tokens", "median_tokens", "short_share"]].rename(
        columns={"rows": "sample_comments", "median_tokens": "median_words", "short_share": "short_comment_share"})
    tot = pd.read_parquet(AGG / "monthly_totals.parquet").pivot_table(index=["subreddit", "month"], columns="type", values="total").reset_index()
    tot = tot.rename(columns={"comment": "comments_total", "submission": "submissions_total"})
    t = pd.read_parquet(AGG / "text_metrics_monthly.parquet")[["subreddit", "month", "mtld", "flesch_median", "vader_mean", "vader_neg_share", "vader_n"]]
    e = pd.read_parquet(AGG / "emoji_monthly.parquet")
    e = e[e.type == "comment"][["subreddit", "month", "per_10k_words"]].rename(columns={"per_10k_words": "emoji_per_10k_words"})
    l = pd.read_parquet(AGG / "lexicon_monthly.parquet")
    l = l[l.type == "comment"]
    br = l[l.tier.isin(["core", "extended"])].groupby(["subreddit", "month"]).agg(
        hits=("hits", "sum"), rows_hit=("rows_with_hit", "sum"), tokens=("tokens", "first"), rows=("rows", "first")).reset_index()
    br["brainrot_per_10k_words"] = br["hits"] * 1e4 / br["tokens"]
    br["brainrot_reach"] = br["rows_hit"] / br["rows"]
    other = l[l.tier.isin(["sigma", "doom"])].pivot_table(index=["subreddit", "month"], columns="tier", values="per_10k_words").reset_index()
    other = other.rename(columns={"sigma": "sigma_per_10k_words", "doom": "doomscroll_per_10k_words"})
    d = ev.load_daily()
    d["month"] = d["day"].dt.to_period("M").dt.to_timestamp()
    cr = d.groupby(["subreddit", "month"])[["hits_crisis", "tokens"]].sum().reset_index()
    cr["crisis_words_per_10k_words"] = cr["hits_crisis"] / cr["tokens"] * 1e4
    df = c.merge(tot, on=["subreddit", "month"]).merge(t, on=["subreddit", "month"]).merge(e, on=["subreddit", "month"]) \
          .merge(br[["subreddit", "month", "brainrot_per_10k_words", "brainrot_reach"]], on=["subreddit", "month"]) \
          .merge(other, on=["subreddit", "month"]).merge(cr[["subreddit", "month", "crisis_words_per_10k_words"]], on=["subreddit", "month"])
    n0 = len(df)
    df = df[(df.tokens >= min_tokens) & (df.vader_n >= 300)].drop(columns=["tokens", "vader_n"])
    df = df.dropna()
    df.insert(1, "group", df["subreddit"].map(SUB2GROUP))
    df["month"] = df["month"].dt.strftime("%Y-%m")
    df["sample_coverage"] = (df["sample_comments"] / df["comments_total"]).clip(upper=1)
    df = df.sort_values(["subreddit", "month"]).reset_index(drop=True)
    assert not df.isna().any().any()
    path = path or OUT / "3_FightClub_draft.csv"
    df.to_csv(path, index=False)
    print(f"{path.name}: {len(df)} rows of {n0} subreddit-months (months with under {min_tokens:,} words or fewer than 300 scored comments dropped), {df.shape[1]} columns")
    return df
