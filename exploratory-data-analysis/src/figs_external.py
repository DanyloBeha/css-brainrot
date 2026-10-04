"""Phase 5 figures: signals from outside Reddit (YouTube trending so far)."""
import matplotlib.pyplot as plt
import pandas as pd

from .config import EXT
from .viz import ACCENT, caption, save, suptitle

MIN_VIDEOS = 1000                      # months with fewer trending videos than this are dropped (partial months at the edges of a file)


def _monthly():
    m = pd.read_parquet(EXT / "youtube_trending_monthly.parquet")
    return m[m.videos >= MIN_VIDEOS].sort_values("month")


def c33():
    """Two panels: brainrot-titled videos per 1,000 trending videos by publish month (rsrishav 2020-24, keshavbansal95 2024-25, with and
    without the Roblox game), and the median views of those videos (log scale, marker size = number of videos)."""
    m = _monthly()
    q = pd.read_parquet(EXT / "youtube_trending_monthly.parquet")
    q["quarter"] = q["month"].dt.to_period("Q")
    qs = q.groupby(["source", "quarter"])[["videos", "brainrot_videos", "brainrot_excl_game"]].sum()
    qs["per_1000"] = qs.brainrot_videos / qs.videos * 1000
    qs["per_1000_excl"] = qs.brainrot_excl_game / qs.videos * 1000
    r_pk = qs.loc["rsrishav"].per_1000.idxmax()
    k_pk = qs.loc["keshavbansal95"].per_1000.idxmax()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7.4), sharex=True, gridspec_kw=dict(height_ratios=[1.2, 1]))
    style = {"rsrishav": ("#7570b3", "-", "2020-24 list (US, GB, CA, IN)"), "keshavbansal95": (ACCENT, "-", "2024-25 list (about 80 countries)")}
    for src, d in m.groupby("source"):
        col, ls, lab = style[src]
        d = d.assign(share=d.brainrot_videos / d.videos * 1000, share_ex=d.brainrot_excl_game / d.videos * 1000)
        a1.plot(d.month, d.share, color=col, lw=2.2, marker="o", ms=4, label=lab)
        if src == "keshavbansal95":
            a1.plot(d.month, d.share_ex, color=col, lw=1.6, ls="--", label="same, without the Roblox game 'Steal a Brainrot'")
        h = d[d.brainrot_videos >= 3]
        a2.scatter(h.month, h.median_views, s=h.brainrot_videos.clip(upper=600) * 0.9 + 15, color=col, alpha=0.75, edgecolor="white", linewidth=0.8)
    for a in (a1, a2):
        a.axvspan(pd.Timestamp("2024-04-15"), pd.Timestamp("2024-10-12"), color="#999", alpha=0.12, lw=0)
    a1.text(pd.Timestamp("2024-07-14"), a1.get_ylim()[1] * 0.6, "no data", ha="center", color="#666", fontsize=10)
    a1.set_ylabel("Brainrot-titled videos per 1,000\ntrending videos")
    a1.legend(frameon=False, loc="upper left", fontsize=10)
    a2.set_yscale("log")
    a2.set_ylabel("Median views of those videos\n(log scale)")
    a2.set_xlabel("Publish month")
    a2.text(0.01, 0.04, "marker size = number of brainrot-titled videos (3 or more); views as recorded when the video was listed",
            transform=a2.transAxes, fontsize=9, color="#555")
    a1.set_xlim(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-10-31"))
    suptitle(fig, f"Brainrot titles on YouTube's trending lists: {qs.loc[('rsrishav', r_pk), 'per_1000']:.0f} per 1,000 videos in {r_pk}, "
                  f"{qs.loc[('keshavbansal95', k_pk), 'per_1000']:.0f} in {k_pk} ({qs.loc[('keshavbansal95', k_pk), 'per_1000_excl']:.0f} without one Roblox game)", y=1.0)
    fig.tight_layout()
    caption(fig, "Source: Kaggle rsrishav/youtube-trending-video-dataset (trending 2020-08 to 2024-04) and keshavbansal95/youtube-trending-videos-dataset "
                 "(trending 2024-10 to 2025-09). Unique videos, matched on title and tags with the brainrot lexicon. The two lists are built differently: "
                 "compare within a list only. Months with under 1,000 videos dropped.")
    save(fig, "C33_youtube_trending_brainrot")
    return fig
