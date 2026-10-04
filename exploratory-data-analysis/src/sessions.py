"""Gap-based sessions from posting timestamps (lurking is invisible). Valid only where every record is present (r/nosurf)."""
import polars as pl


def sessions(lf: pl.LazyFrame, gap_minutes=30) -> pl.LazyFrame:
    """One row per session: author, start, end, messages, minutes. `lf` needs author_id and ts (datetime)."""
    return (lf.filter(pl.col("author_id").is_not_null()).sort(["author_id", "ts"])
            .with_columns((pl.col("ts").diff().over("author_id") > pl.duration(minutes=gap_minutes))
                          .fill_null(True).cast(pl.Int32).alias("new"))
            .with_columns(pl.col("new").cum_sum().over("author_id").alias("sess"))
            .group_by(["author_id", "sess"])
            .agg(pl.col("ts").min().alias("start"), pl.col("ts").max().alias("end"), pl.len().alias("n_msgs"))
            .with_columns((pl.col("end") - pl.col("start")).dt.total_minutes().alias("minutes")))
