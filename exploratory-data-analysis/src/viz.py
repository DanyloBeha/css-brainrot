"""Plot style, palette and helpers. Every figure is saved through save()."""
import matplotlib.pyplot as plt

from .config import FIG

ACCENT, GRAY = "#d95f02", "#9a9a9a"
GROUP_COLORS = {
    "short_form": "#d95f02",
    "long_form": "#1b9e77",
    "baseline": "#7570b3",
    "reflective": "#66a61e",
    "news": "#e7298a",
    "control": GRAY,
}
SUB_COLORS = {                     # subreddit -> its group color
    "memes": "#d95f02", "teenagers": "#d95f02",
    "books": "#1b9e77", "explainlikeimfive": "#1b9e77",
    "todayilearned": "#7570b3", "nosurf": "#66a61e",
    "worldnews": "#e7298a", "news": "#e7298a",
}


def set_style():
    plt.rcParams.update({
        "figure.figsize": (9, 5), "font.size": 12, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
        "grid.alpha": 0.25, "figure.dpi": 100,
    })


def finding_title(ax, title, subtitle=""):
    """Finding as title; metric and unit as a smaller subtitle."""
    ax.set_title(title, loc="left", pad=22)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=10, color="#555")


def suptitle(fig, text, width=88, y=1.0):
    """Bold left-aligned figure title, wrapped so a long finding cannot widen the canvas."""
    import textwrap
    fig.suptitle(textwrap.fill(text, width), x=0.01, ha="left", fontweight="bold", fontsize=13, y=y)


def caption(fig, text):
    """Source / caveat line under the figure."""
    fig.text(0.01, -0.02, text, fontsize=9, color="#555", ha="left", va="top", wrap=True)


def end_label(ax, x, y, text, color):
    ax.text(x, y, " " + text, color=color, va="center", fontsize=11)


def event_line(ax, date, label, ypos=0.97):
    """Dashed vertical line with a short label; ypos is an axes fraction (stagger to avoid overlap)."""
    ax.axvline(date, color="black", lw=1, ls="--", alpha=0.7)
    ax.annotate(label, (date, ypos), xycoords=("data", "axes fraction"), xytext=(4, 0),
                textcoords="offset points", va="top", fontsize=10)


def highlight_vs_gray(ax, wide_df, highlight):
    """wide_df: index=time, columns=series. Everything gray except `highlight`."""
    for c in wide_df.columns:
        if c != highlight:
            ax.plot(wide_df.index, wide_df[c], color=GRAY, lw=1, alpha=0.6)
    ax.plot(wide_df.index, wide_df[highlight], color=ACCENT, lw=2.5)
    end_label(ax, wide_df.index[-1], wide_df[highlight].iloc[-1], highlight, ACCENT)


def save(fig, chart_id):
    """chart_id like 'C10_median_length' -> figures/C10_median_length.png"""
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{chart_id}.png", dpi=200, bbox_inches="tight")
