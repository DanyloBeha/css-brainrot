"""Phase 2 figures C01-C09. Each function reads cached aggregates, saves the PNG, returns the figure.

Titles are built from the data, so a number in a title can never drift from the chart.
"""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text

from .config import AGG, EVENTS
from .viz import ACCENT, GRAY, SUB_COLORS, caption, event_line, finding_title, save

ORDER = ["memes", "teenagers", "books", "explainlikeimfive", "todayilearned", "nosurf"]
NAMES = {s: f"r/{s}" for s in ORDER}
TYPE_COLORS = {"comment": "#4d4d4d", "submission": ACCENT}
SAMPLE_NOTE = ("Source: Arctic Shift, six subreddits, 2012-01 to 2026-09. Rates and medians come from a "
               "random time-slot sample (~10k comments, ~2k posts per subreddit-month).")


def load(name):
    return pd.read_parquet(AGG / f"{name}.parquet")


def _m(n, d=1):
    return f"{n / 1e6:.{d}f}M"


def _lines_ordered(ax, df, value, color_by="subreddit", label_dx=" "):
    """Plot one line per subreddit in group color and return text labels for adjust_text."""
    texts = []
    for s in ORDER:
        d = df[df[color_by] == s].dropna(subset=[value])
        if d.empty:
            continue
        ax.plot(d["month"], d[value], color=SUB_COLORS[s], lw=2)
        texts.append(ax.text(d["month"].iloc[-1], d[value].iloc[-1], label_dx + NAMES[s],
                             color=SUB_COLORS[s], fontsize=11, va="center"))
    return texts


# ---------------------------------------------------------------- C01
def c01():
    """Stacked columns: exact monthly comments and submissions of the six subreddits together (from the monthly totals, not the sample)."""
    t = load("monthly_totals")
    m = t.groupby(["month", "type"])["total"].sum().unstack().fillna(0)
    total = m.sum(axis=1)
    peak = total.idxmax()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(m.index, m["comment"] / 1e6, width=26, color=TYPE_COLORS["comment"])
    ax.bar(m.index, m["submission"] / 1e6, width=26, bottom=m["comment"] / 1e6, color=TYPE_COLORS["submission"])
    ax.set_ylabel("Records per month (millions)")
    ax.margins(x=0.01)
    finding_title(ax, f"Activity peaked in {peak:%B %Y} at {_m(total[peak])} records and fell to "
                      f"{_m(total.iloc[-1])} by {total.index[-1]:%B %Y}",
                  "Exact monthly counts of comments and submissions, six subreddits together")
    ax.text(pd.Timestamp("2012-09-01"), 1.9, "Comments (dark gray)", color=TYPE_COLORS["comment"], fontsize=12, fontweight="bold")
    ratio = m["comment"].sum() / m["submission"].sum()
    ax.annotate(f"Submissions (orange): 1 for every\n{ratio:.0f} comments over the whole period",
                (peak, total[peak] / 1e6), xytext=(pd.Timestamp("2013-06-01"), 5.9),
                color=TYPE_COLORS["submission"], fontsize=11, arrowprops=dict(arrowstyle="-", color=GRAY))
    ax.set_ylim(0, total.max() / 1e6 * 1.08)
    caption(fig, "Source: Arctic Shift monthly totals (all records, not the sample). Subreddits: books, explainlikeimfive, "
                 "memes, nosurf, teenagers, todayilearned.")
    save(fig, "C01_records_per_month")
    return fig


# ---------------------------------------------------------------- C02
def c02():
    """Stacked bars: for each subreddit, the part of its records that is in our sample (dark) and the part we did not download (light)."""
    w = load("sample_weights")
    g = w.groupby("subreddit")[["total", "raw_rows"]].sum().reindex(ORDER)
    g["cov"] = g["raw_rows"] / g["total"]
    g = g.sort_values("total", ascending=False)
    top2 = g.loc[["memes", "teenagers"]]
    share = top2["total"].sum() / g["total"].sum()
    cov_top2 = top2["raw_rows"].sum() / top2["total"].sum()
    fig, ax = plt.subplots(figsize=(10, 4.4))
    for yi, (s_, r) in zip(np.arange(len(g))[::-1], g.iterrows()):
        ax.barh(yi, r["cov"] * 100, color=SUB_COLORS[s_], height=0.62)
        ax.barh(yi, (1 - r["cov"]) * 100, left=r["cov"] * 100, color=SUB_COLORS[s_], alpha=0.25, height=0.62)
        ax.text(101.5, yi, f"{r['raw_rows'] / 1e6:.1f}M of {r['total'] / 1e6:.1f}M records ({r['cov']:.1%})", va="center", fontsize=10.5)
    ax.set_yticks(np.arange(len(g))[::-1], [NAMES[s_] for s_ in g.index])
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Share of the subreddit's records (dark = in our sample, light = not downloaded)")
    ax.grid(axis="y", alpha=0)
    ax.grid(axis="x", alpha=0.25)
    finding_title(ax, f"r/memes and r/teenagers hold {share:.0%} of all records, yet our sample covers only {cov_top2:.1%} of them",
                  "Records (comments + submissions) in the full archive vs. in our sample, 2012-2026")
    caption(fig, "Source: Arctic Shift monthly totals vs. downloaded sample (raw rows before cleaning). Only r/nosurf is complete.")
    fig.subplots_adjust(right=0.62)
    save(fig, "C02_subreddits_carrying_data")
    return fig


# ---------------------------------------------------------------- C03 (revised, see research log)
SHORT_EVENTS = {"COVID-19 pandemic declared": "COVID-19 declared", "Russia full-scale invasion of Ukraine": "Ukraine invasion",
                "Hamas attack / Gaza war begins": "Gaza war", "Assassination of Charlie Kirk": "Kirk"}


def add_events(ax, ypos=(0.97, 0.89, 0.81, 0.73)):
    for (k, v), y in zip(EVENTS.items(), ypos):
        event_line(ax, pd.Timestamp(v), SHORT_EVENTS.get(k, k), ypos=y)


def c03():
    """Line: distinct commenting authors per month in r/nosurf (complete data), 3-month mean, with the four event dates."""
    o = load("overview_counts")
    d = o[(o.subreddit == "nosurf") & (o.type == "comment")].set_index("month").sort_index()
    s = d["authors"]
    roll = s.rolling(3, center=True, min_periods=1).mean()
    base = s[s.index.year <= 2015].mean()
    last = s[s.index.year == 2025].mean()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(s.index, s, color=GRAY, lw=1, alpha=0.8)
    ax.plot(roll.index, roll, color=SUB_COLORS["nosurf"], lw=2.5)
    ax.set_ylabel("Distinct commenting authors per month")
    ax.set_ylim(0, s.max() * 1.1)
    finding_title(ax, f"r/nosurf grew from ~{base:.0f} commenters a month (2012-15) to ~{last:,.0f} in 2025",
                  "Complete data for r/nosurf (all comments are in the sample); gray = monthly value, green = 3-month mean")
    add_events(ax)
    caption(fig, "Source: Arctic Shift, r/nosurf comments, bots and deleted accounts excluded. Other subreddits are not shown: their "
                 "sample has a fixed size, so author counts there would only mirror the sampling plan.")
    save(fig, "C03_nosurf_authors_per_month")
    return fig


def c03b():
    """Small multiples: share of sampled comments that are removed/deleted or written by bots, per subreddit and month (raw sample, before cleaning)."""
    q = load("raw_quality_monthly")
    q = q[q.type == "comment"].sort_values(["subreddit", "month"]).copy()
    q["year"] = q["month"].dt.year
    early = q[q.year <= 2022]["removed_rows"].sum() / q[q.year <= 2022]["raw_rows"].sum()
    late = q[q.year >= 2024]["removed_rows"].sum() / q[q.year >= 2024]["raw_rows"].sum()
    ns = q[q.subreddit == "nosurf"].copy()
    ns_peak = (ns["bot_rows"].rolling(12, min_periods=12).sum() / ns["raw_rows"].rolling(12, min_periods=12).sum()).max()
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.6), sharex=True, sharey=True)
    for ax, s in zip(axes.flat, ORDER):
        d = q[q.subreddit == s].set_index("month")
        ax.plot(d.index, d["removed_rows"].div(d["raw_rows"]).rolling(6, min_periods=1).mean() * 100, color=GRAY, lw=2)
        ax.plot(d.index, d["bot_rows"].div(d["raw_rows"]).rolling(6, min_periods=1).mean() * 100, color=ACCENT, lw=2)
        ax.set_title(NAMES[s], fontsize=11, loc="left", color=SUB_COLORS[s])
        ax.set_ylim(0, 22)
        ax.xaxis.set_major_locator(mdates.YearLocator(6, month=1, day=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0, 1].text(pd.Timestamp("2012-06-01"), 15, "removed / deleted", color="#666", fontsize=10)
    axes[0, 1].text(pd.Timestamp("2018-06-01"), 4.5, "bots", color=ACCENT, fontsize=10, fontweight="bold")
    for ax in axes[:, 0]:
        ax.set_ylabel("% of sampled comments")
    fig.suptitle(f"Removed or deleted comments fell from {early:.0%} (2012-22) to {late:.0%} (2024-26); "
                 f"bots reach {ns_peak:.0%} of r/nosurf comments", x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.0)
    fig.tight_layout()
    caption(fig, "Source: raw Arctic Shift sample before cleaning. 6-month rolling mean. These rows are dropped before the text analysis; "
                 "bots = AutoModerator and names ending in 'bot'.")
    save(fig, "C03b_removed_and_bot_share")
    return fig


# ---------------------------------------------------------------- C04
def _top_curve(d, grid):
    """Share of messages written by the most active `grid` fraction of authors."""
    d = d.sort_values("msgs", ascending=False)
    ca = np.r_[0, d["authors"].cumsum() / d["authors"].sum()]
    cm = np.r_[0, (d["msgs"] * d["authors"]).cumsum() / (d["msgs"] * d["authors"]).sum()]
    return np.interp(grid, ca, cm)


def c04():
    """Share of all messages written by the most active x% of authors (log x-axis); exact for r/nosurf, sample-only for the others."""
    a = load("author_activity")
    grid = np.logspace(-3, 0, 200)
    fig, ax = plt.subplots(figsize=(8, 5.4))
    ax.plot([0.001, 1], [0.001, 1], color="#bbb", lw=1, ls=":")
    ax.axvline(0.01, color="#bbb", lw=0.8)
    at1 = {}
    for s in ORDER:
        y = _top_curve(a[a.subreddit == s], grid)
        at1[s] = float(np.interp(0.01, grid, y))
        if s == "nosurf":
            continue
        ax.plot(grid, y, color=GRAY, lw=1.4, alpha=0.9)
    y = _top_curve(a[a.subreddit == "nosurf"], grid)
    ax.plot(grid, y, color=SUB_COLORS["nosurf"], lw=3)
    ax.plot([0.01], [at1["nosurf"]], "o", color=SUB_COLORS["nosurf"], ms=8, mec="white", mew=2, zorder=5)
    ax.annotate(f"r/nosurf: the most active 1% of authors\nwrite {at1['nosurf']:.0%} of all messages",
                (0.01, at1["nosurf"]), xytext=(0.0013, 0.80), fontsize=11, color="#222",
                arrowprops=dict(arrowstyle="-", color=SUB_COLORS["nosurf"]))
    others = [v for k, v in at1.items() if k != "nosurf"]
    ax.annotate("other five subreddits\n(sample only)", (0.12, float(np.interp(0.12, grid, _top_curve(a[a.subreddit == "todayilearned"], grid)))),
                xytext=(0.2, 0.25), fontsize=10, color="#666", arrowprops=dict(arrowstyle="-", color="#999"))
    ax.set_xscale("log")
    ax.set_xlim(0.001, 1.6)
    ax.set_ylim(0, 1.02)
    ax.set_xticks([0.001, 0.01, 0.1, 1], ["0.1%", "1%", "10%", "100%"])
    ax.set_xlabel("Most active share of authors (log scale)")
    ax.set_ylabel("Share of all messages they write")
    ax.grid(axis="x", alpha=0.25)
    finding_title(ax, f"Activity is concentrated: the top 1% of r/nosurf authors write {at1['nosurf']:.0%} of messages",
                  f"Messages per author; the other five subreddits (sample only) give {min(others):.0%}-{max(others):.0%} at the 1% mark")
    caption(fig, "r/nosurf is complete (green). Gray curves use only the sample, which hides repeat posting, so true concentration "
                 "there is likely higher. Comments + submissions, deleted accounts excluded.")
    save(fig, "C04_author_concentration")
    return fig


# ---------------------------------------------------------------- C05
def _wq(values, weights, q):
    o = np.argsort(values)
    v, w = np.asarray(values)[o], np.asarray(weights)[o]
    c = np.cumsum(w) / w.sum()
    return v[np.searchsorted(c, q)]


def c05():
    """Range plot: median (dot), middle half (thick bar) and 10th-90th percentile (thin line) of comment length in words per subreddit,
    log x-axis, months weighted by true volume."""
    h = load("length_hist")
    h = h[h.type == "comment"].groupby(["subreddit", "value"])["est_rows"].sum().reset_index()
    q = {s_: [_wq(d["value"], d["est_rows"], p_) for p_ in (0.1, 0.25, 0.5, 0.75, 0.9)] for s_, d in h.groupby("subreddit")}
    order = sorted(ORDER, key=lambda k: q[k][2])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for yi, s_ in zip(np.arange(len(order))[::-1], order):
        p10, p25, p50, p75, p90 = [max(v, 1) for v in q[s_]]
        ax.plot([p10, p90], [yi, yi], color=SUB_COLORS[s_], lw=2, alpha=0.55)
        ax.plot([p25, p75], [yi, yi], color=SUB_COLORS[s_], lw=10, solid_capstyle="butt")
        ax.plot([p50], [yi], "o", color="white", ms=9, mec="#222", mew=1.6, zorder=5)
        ax.text(p90 * 1.12, yi, f"median {p50:.0f} words", va="center", fontsize=10.5)
    ax.set_yticks(np.arange(len(order))[::-1], [NAMES[s_] for s_ in order])
    ax.set_xscale("log")
    ax.set_xlim(1, 600)
    ax.set_xticks([1, 3, 10, 30, 100, 300], ["1", "3", "10", "30", "100", "300"])
    ax.set_xlabel("Comment length in words (log scale)")
    ax.grid(axis="y", alpha=0)
    ax.grid(axis="x", alpha=0.25)
    lo, hi = order[0], order[-1]
    finding_title(ax, f"Typical comment: {q[lo][2]:.0f} words in {NAMES[lo]} vs {q[hi][2]:.0f} in {NAMES[hi]}",
                  "Dot = median, thick bar = middle half of comments, thin line = 10th to 90th percentile; all years pooled")
    caption(fig, SAMPLE_NOTE + " Months are weighted by true monthly volume. Words = tokens of letters/digits/apostrophes, URLs removed.")
    save(fig, "C05_comment_length_by_subreddit")
    return fig


# ---------------------------------------------------------------- C06
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _smooth_hours(m):
    """3-hour circular moving average along the hour axis (sampled cells are noisy)."""
    a = m.to_numpy()
    return pd.DataFrame((np.roll(a, 1, 1) + a + np.roll(a, -1, 1)) / 3, index=m.index, columns=m.columns)


def c06():
    """Heatmaps: weighted share of comments by UTC weekday and hour per subreddit, smoothed over 3 hours (BuGn)."""
    h = load("hour_dow")
    h = h[h.type == "comment"]
    both = h.groupby(["dow", "hour"])["est_rows"].sum().unstack()
    both = _smooth_hours(both / both.to_numpy().sum() * 100)
    peak_h = both.sum(axis=0).idxmax()
    day = both.sum(axis=1)
    wk, we = day[[1, 2, 3, 4, 5]].mean(), day[[6, 7]].mean()
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.8), sharex=True, sharey=True)
    vmax = 0
    mats = {}
    for s in ORDER:
        m = h[h.subreddit == s].groupby(["dow", "hour"])["est_rows"].sum().unstack()
        m = _smooth_hours(m / m.to_numpy().sum() * 100)
        mats[s] = m
        vmax = max(vmax, m.to_numpy().max())
    for ax, s in zip(axes.flat, ORDER):
        im = ax.imshow(mats[s].to_numpy(), cmap="BuGn", vmin=0, vmax=vmax, aspect="auto")
        ax.set_title(NAMES[s], fontsize=11, loc="left", color=SUB_COLORS[s])
        ax.grid(False)
        ax.set_yticks(range(7), DOW)
        ax.set_xticks([0, 6, 12, 18, 23])
    for ax in axes[1]:
        ax.set_xlabel("Hour of day (UTC)")
    fig.suptitle(f"Posting peaks around {peak_h}:00 UTC; a weekend day carries {1 - we / wk:.0%} less than a weekday",
                 x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.0)
    fig.tight_layout(rect=(0, 0, 0.9, 1))
    cax = fig.add_axes([0.92, 0.18, 0.015, 0.62])
    fig.colorbar(im, cax=cax, label="% of the subreddit's weekly comments")
    caption(fig, SAMPLE_NOTE + " Weighted by true monthly volume, smoothed over 3 hours (few sampled slots per cell). UTC mixes time zones.")
    save(fig, "C06_hour_by_weekday")
    return fig


# ---------------------------------------------------------------- C07
def c07():
    """Lines: exact monthly comments divided by submissions per subreddit, 12-month mean, log y-axis."""
    t = load("monthly_totals").pivot_table(index=["subreddit", "month"], columns="type", values="total").reset_index()
    t["ratio"] = t["comment"] / t["submission"]
    t = t.sort_values(["subreddit", "month"])
    t["roll"] = t.groupby("subreddit")["ratio"].transform(lambda s: s.rolling(12, min_periods=6).mean())
    t["year"] = t["month"].dt.year
    yr = t.groupby(["subreddit", "year"])[["comment", "submission"]].sum()
    yr["r"] = yr["comment"] / yr["submission"]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    texts = _lines_ordered(ax, t, "roll")
    ax.set_yscale("log")
    ax.set_ylabel("Comments per submission (log scale, 12-month mean)")
    ax.grid(axis="y", which="both", alpha=0.2)
    ax.set_xlim(t["month"].min(), t["month"].max() + pd.Timedelta(days=900))
    ax.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(2012, 2027, 2)]), [str(y) for y in range(2012, 2027, 2)])
    ch = {s: yr.loc[(s, 2025), "r"] / yr.loc[(s, 2015), "r"] for s in ORDER if (s, 2015) in yr.index}
    s_up = max(ch, key=ch.get)
    s_dn = min(ch, key=ch.get)
    f = lambda v: f"{v:.1f}" if v < 10 else f"{v:.0f}"
    second = (f"; {NAMES[s_dn]} fell ({f(yr.loc[(s_dn, 2015), 'r'])} to {f(yr.loc[(s_dn, 2025), 'r'])})" if ch[s_dn] < 0.95 else "")
    finding_title(ax, f"Comments per post rose most in {NAMES[s_up]} ({f(yr.loc[(s_up, 2015), 'r'])} in 2015 to "
                      f"{f(yr.loc[(s_up, 2025), 'r'])} in 2025){second}",
                  "Exact monthly comment total divided by submission total, 12-month mean")
    adjust_text(texts, ax=ax, only_move={"text": "y"})
    caption(fig, "Source: Arctic Shift monthly totals (all records). Ratio mixes comment culture and posting culture: a post-heavy "
                 "feed (memes) has few comments each.")
    save(fig, "C07_comments_per_submission")
    return fig


# ---------------------------------------------------------------- C08
BANDS = [("<= 0", -1e9, 0), ("1", 1, 1), ("2-9", 2, 9), ("10-99", 10, 99), ("100+", 100, 1e9)]
BAND_COLORS = ["#b0b0b0", "#e5f5f9", "#99d8c9", "#41ae76", "#00441b"]


def c08():
    """Left: share of comments per score band by subreddit. Right: share of comments and submissions reaching a score of 10, by length bin."""
    sh = load("score_hist")
    sh = sh[sh.type == "comment"]
    sbl = load("score_by_length")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw=dict(width_ratios=[1.25, 1]))
    shares = {}
    for sname in ORDER:
        d = sh[sh.subreddit == sname].groupby("value")["est_rows"].sum()
        tot = d.sum()
        shares[sname] = [d[(d.index >= lo) & (d.index <= hi)].sum() / tot for _, lo, hi in BANDS]
    order = sorted(ORDER, key=lambda k: shares[k][0] + shares[k][1], reverse=True)
    y = np.arange(len(order))[::-1]
    for yi, sname in zip(y, order):
        left = 0
        for (lab, _, _), col, v in zip(BANDS, BAND_COLORS, shares[sname]):
            a1.barh(yi, v * 100, left=left * 100, color=col, height=0.66, edgecolor="white", lw=1)
            if v > 0.06:
                a1.text((left + v / 2) * 100, yi, f"{v:.0%}", ha="center", va="center", fontsize=10,
                        color="white" if lab in ("10-99", "100+") else "#222")
            left += v
    a1.set_yticks(y, [NAMES[k] for k in order])
    a1.grid(False)
    a1.set_xlim(0, 100)
    a1.set_xlabel("Share of comments (%)")
    a1.set_title("Comment score bands", loc="left", fontsize=11, fontweight="normal")
    from matplotlib.patches import Patch
    a1.legend([Patch(facecolor=c, edgecolor="#999") for c in BAND_COLORS], [b[0] for b in BANDS], title="Score",
              ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False, fontsize=10, title_fontsize=10)
    # share with score >= 10 by length bin (pooled)
    rows = {}
    for typ in ("comment", "submission"):
        d = sbl[sbl.type == typ].groupby("len_bin")[["est_rows", "est_ge10", "rows"]].sum()
        d = d[d["rows"] >= 2000]
        rows[typ] = (2 ** d.index.to_numpy(), (d["est_ge10"] / d["est_rows"]).to_numpy() * 100)
    for typ, col in (("comment", "#4d4d4d"), ("submission", ACCENT)):
        x, v = rows[typ]
        a2.plot(x, v, "-o", color=col, lw=2, ms=5)
        a2.text(x[-1], v[-1], f" {typ}s", color=col, fontsize=11, va="center")
    a2.set_xscale("log")
    a2.set_xlim(1, 4000)
    a2.set_ylim(0, None)
    a2.set_xlabel("Length in words (log scale, bins of x2)")
    a2.set_ylabel("Share scoring 10 or more (%)")
    a2.set_title("Reaching a score of 10, by length", loc="left", fontsize=11, fontweight="normal")
    xs, vs = rows["comment"]
    low, high = vs[1], vs[np.argmax(xs >= 32)]
    both = {k: shares[k][0] + shares[k][1] for k in ORDER}
    fig.suptitle(f"{min(both.values()):.0%}-{max(both.values()):.0%} of comments end at a score of 1 or less; "
                 f"{low:.0f}% of 2-3-word comments reach 10 vs {high:.0f}% at 32+ words",
                 x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.03)
    fig.tight_layout()
    caption(fig, SAMPLE_NOTE + " Scores are the value at download time (not at posting time), so old and new months are not strictly comparable.")
    save(fig, "C08_score_distribution_and_length")
    return fig


# ---------------------------------------------------------------- C09
def anomalies(top=5, min_gap_days=30, min_base=20):
    d = load("daily_full_coverage")
    d = d[(d.subreddit == "nosurf") & (d.type == "comment")]
    d = d.set_index(pd.to_datetime(d["day"]))["rows"].asfreq("D", fill_value=0)
    base = d.rolling(29, center=True, min_periods=15).median()
    z = ((d - base) / np.sqrt(base.clip(lower=1))).where(base >= min_base).dropna()   # Poisson-style z, busy periods only
    picks = []
    for day in z.sort_values(ascending=False).index:
        if all(abs((day - p).days) > min_gap_days for p in picks):
            picks.append(day)
        if len(picks) == top:
            break
    return d, z, sorted(picks)


def c09():
    """Line: daily r/nosurf comments with 7-day mean; the five strongest one-day spikes (Poisson-style z against a 29-day median) and the event dates."""
    d, z, picks = anomalies()
    roll = d.rolling(7, center=True, min_periods=4).mean()
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(d.index, d, color=GRAY, lw=0.7, alpha=0.8)
    ax.plot(roll.index, roll, color=SUB_COLORS["nosurf"], lw=1.8)
    ax.set_ylabel("Comments per day in r/nosurf")
    ax.set_ylim(0, d.max() * 1.12)
    pk = d.idxmax()
    prior = d[pk - pd.Timedelta(days=30):pk - pd.Timedelta(days=1)].mean()
    finding_title(ax, f"r/nosurf's busiest day was {pk:%d %b %Y}: {d.max():,} comments, {d.max() / prior:.1f}x the month before",
                  "Daily comments (gray) and 7-day mean (green); dots = five strongest one-day spikes vs the local 29-day median")
    texts = []
    for p_ in picks:
        ax.plot([p_], [d[p_]], "o", color="#222", ms=6, mec="white", mew=1.5)
        texts.append(ax.text(p_, d[p_], f"{p_:%d %b %Y}", fontsize=9, color="#222", ha="center", va="bottom"))
    add_events(ax)
    adjust_text(texts, ax=ax, only_move={"text": "y"})
    caption(fig, "Source: Arctic Shift, r/nosurf comments (complete, bots and removed text excluded). Only r/nosurf has full daily "
                 "coverage; larger subreddits are sampled in time slots.")
    save(fig, "C09_nosurf_daily_volume")
    return fig
