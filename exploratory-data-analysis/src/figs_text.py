"""Phase 3 figures (text metrics and the brainrot lexicon). Titles are computed from the data."""
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text

from .figs_overview import NAMES, ORDER, SAMPLE_NOTE, load
from .viz import GRAY, SUB_COLORS, caption, finding_title, save, suptitle

YEARS = pd.to_datetime([f"{y}-01-01" for y in range(2012, 2027, 2)])


def _xaxis(ax, right_pad_days=0):
    ax.set_xticks(YEARS, [str(d.year) for d in YEARS])
    lo, hi = ax.get_xlim()
    ax.set_xlim(lo, hi + right_pad_days)


def _roll(df, col, w=12, minp=6):
    df = df.sort_values(["subreddit", "month"]).copy()
    df["roll"] = df.groupby("subreddit")[col].transform(lambda s: s.rolling(w, min_periods=minp).mean())
    return df


def _lines(ax, df, ycol="roll", pad_days=900):
    texts = []
    for s in ORDER:
        d = df[df.subreddit == s].dropna(subset=[ycol])
        if d.empty:
            continue
        ax.plot(d["month"], d[ycol], color=SUB_COLORS[s], lw=2.2)
        texts.append(ax.text(d["month"].iloc[-1] + pd.Timedelta(days=60), d[ycol].iloc[-1], NAMES[s],
                             color=SUB_COLORS[s], fontsize=11, va="center"))
    _xaxis(ax, pd.Timedelta(days=pad_days).days)
    return texts


# ---------------------------------------------------------------- C10
def c10():
    """Lines: median words per comment per subreddit-month, 12-month mean, months under 50,000 words dropped."""
    o = load("overview_counts")
    c = _roll(o[(o.type == "comment") & (o.tokens >= 50_000)], "median_tokens")
    st = {}
    for s, d in c.groupby("subreddit"):
        d = d.dropna(subset=["roll"])
        st[s] = (d["roll"].iloc[0], d.loc[d["roll"].idxmin()], d["roll"].iloc[-1])
    fig, ax = plt.subplots(figsize=(10, 5.4))
    texts = _lines(ax, c)
    ax.set_ylabel("Median comment length (words, 12-month mean)")
    ax.set_ylim(0, None)
    t_first, t_min, t_last = st["teenagers"]
    m_first, m_min, m_last = st["memes"]
    finding_title(ax, f"Short-form comments shrank, then recovered: r/teenagers {t_first:.0f} to {t_min['roll']:.0f} to {t_last:.0f} words, "
                      f"r/memes {m_first:.0f} to {m_min['roll']:.0f} to {m_last:.0f}",
                  "Median words per comment by month; title values: first 12 months with enough text, lowest point, last 12 months. Long-form stays flat")
    adjust_text(texts, ax=ax, only_move={"text": "y"})
    ax.annotate(f"low {t_min['month']:%Y}", (t_min["month"], t_min["roll"]), xytext=(0, -22), textcoords="offset points",
                ha="center", fontsize=9, color=SUB_COLORS["teenagers"], arrowprops=dict(arrowstyle="-", color="#aaa"))
    ax.annotate(f"low {m_min['month']:%Y}", (m_min["month"], m_min["roll"]), xytext=(0, -22), textcoords="offset points",
                ha="center", fontsize=9, color=SUB_COLORS["memes"], arrowprops=dict(arrowstyle="-", color="#aaa"))
    caption(fig, SAMPLE_NOTE + " Bots and removed text excluded. The median is of whole comments, so it is robust to a few long ones.")
    save(fig, "C10_median_comment_length")
    return fig


# ---------------------------------------------------------------- C13
def c13():
    """Lines: share of comments with 5 words or fewer per subreddit-month, 12-month mean."""
    o = load("overview_counts")
    c = _roll(o[(o.type == "comment") & (o.tokens >= 50_000)].assign(pct=lambda d: d["short_share"] * 100), "pct")
    last = c.groupby("subreddit")["roll"].last()
    peak = c.loc[c.groupby("subreddit")["roll"].idxmax()].set_index("subreddit")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    texts = _lines(ax, c)
    ax.set_ylabel("Comments of 5 words or fewer (%, 12-month mean)")
    ax.set_ylim(0, None)
    finding_title(ax, f"At their peak {peak.loc['teenagers', 'roll']:.0f}% of r/teenagers and {peak.loc['memes', 'roll']:.0f}% of r/memes "
                      f"comments had 5 words or fewer; r/books stays near {last['books']:.0f}%",
                  "Share of very short comments per month")
    adjust_text(texts, ax=ax, only_move={"text": "y"})
    caption(fig, SAMPLE_NOTE + " Bots and removed text excluded.")
    save(fig, "C13_very_short_share")
    return fig


# ---------------------------------------------------------------- C15 / C16
def _lex(types=("comment",), tiers=("core", "extended")):
    l = load("lexicon_monthly")
    l = l[l.type.isin(types) & l.tier.isin(tiers)]
    g = l.groupby(["type", "subreddit", "month"]).agg(hits=("hits", "sum"), tokens=("tokens", "first"), rows=("rows", "first"),
                                                       rows_hit=("rows_with_hit", "sum"), ok=("enough_tokens", "first")).reset_index()
    g["per10k"] = g["hits"] * 1e4 / g["tokens"]
    g["reach"] = g["rows_hit"] / g["rows"] * 100        # rows_hit slightly overcounts rows hit by both tiers; negligible
    return g[g.ok]


def _small_multiples(col, ylabel, fname, title, caption_txt, ylim=None):
    g = _lex()
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.8), sharex=True, sharey=True)
    for ax, s in zip(axes.flat, ORDER):
        d = g[g.subreddit == s].sort_values("month")
        ax.plot(d["month"], d[col], color=SUB_COLORS[s], lw=0.8, alpha=0.35)
        ax.plot(d["month"], d[col].rolling(3, min_periods=1, center=True).mean(), color=SUB_COLORS[s], lw=2.2)
        ax.set_title(NAMES[s], fontsize=11, loc="left", color=SUB_COLORS[s])
        ax.xaxis.set_major_locator(mdates.YearLocator(6, month=1, day=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel)
    if ylim:
        axes[0, 0].set_ylim(*ylim)
    suptitle(fig, title(g), y=1.04)
    fig.tight_layout()
    caption(fig, caption_txt)
    save(fig, fname)
    return fig


def c15():
    """Small multiples: core + extended brainrot terms per 10,000 words (comments), month and 3-month mean, shared y-axis."""
    def title(g):
        pk = g.loc[g.groupby("subreddit")["per10k"].idxmax()].set_index("subreddit")
        pre = g[g.month < "2022-01-01"]["per10k"].max()
        return (f"Brainrot terms appeared from 2022: peaks of {pk.loc['memes', 'per10k']:.1f} (r/memes, {pk.loc['memes', 'month']:%b %Y}) and "
                f"{pk.loc['teenagers', 'per10k']:.1f} (r/teenagers, {pk.loc['teenagers', 'month']:%b %Y}) per 10,000 words; "
                f"before 2022 never above {pre:.1f}")
    return _small_multiples("per10k", "Hits per 10,000 words", "C15_brainrot_per_10k_words", title,
                            SAMPLE_NOTE + " Terms: brain rot, skibidi, rizz, gyatt, fanum tax, mewing, tralalero, tung tung. Comments only, "
                                          "months with under 50,000 words dropped; light line = month, bold = 3-month mean.")


def c16():
    """Small multiples: reach = share of comments containing at least one core or extended term."""
    def title(g):
        pk = g.loc[g.groupby("subreddit")["reach"].idxmax()].set_index("subreddit")
        return (f"At the peak about 1 in {100 / pk.loc['memes', 'reach']:.0f} r/memes comments contained a brainrot term; "
                f"in r/teenagers 1 in {100 / pk.loc['teenagers', 'reach']:.0f}")
    return _small_multiples("reach", "Comments with a term (%)", "C16_brainrot_reach", title,
                            SAMPLE_NOTE + " Reach = share of comments containing at least one term from the core or extended list.")


def c15b():
    """Stream graph: brainrot terms per 10,000 words (all six subreddits' comments pooled, 3-month mean), stacked by term with a centered
    baseline, so the band thickness is the absolute rate of each term. 'brain rot' includes brainrot and brain-rot."""
    t = load("lexicon_terms_by_month")
    t = t[(t.type == "comment") & t.tier.isin(["core", "extended"])].copy()
    t["g"] = t["term"].str.replace("-", " ", regex=False).map(lambda w: "rizz" if w.startswith("rizz") else "brain rot" if w.startswith("brain") else w)
    cols = ["rizz", "skibidi", "gyatt", "tung tung", "brain rot"]
    t = t[t.g.isin(cols)]
    tok = load("overview_counts")
    tok = tok[tok.type == "comment"].groupby("month")["tokens"].sum()
    full = pd.date_range("2022-01-01", "2026-09-01", freq="MS")
    p = t.groupby(["month", "g"])["n"].sum().unstack().reindex(columns=cols).reindex(full).fillna(0)
    rate = p.div(tok.reindex(full), axis=0) * 1e4
    rate = rate.rolling(3, min_periods=1, center=True).mean()
    palette = ["#e6ab02", "#d95f02", "#a6761d", "#7570b3", "#1b9e77"]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.stackplot(rate.index, rate.T.to_numpy(), colors=palette, baseline="wiggle", alpha=0.95, edgecolor="white", linewidth=0.5)
    ax.set_yticks([])
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    tot = rate.sum(axis=1)
    peak = tot.idxmax()
    # direct labels: the exact stack position of matplotlib's "wiggle" baseline, so each label sits inside its own band
    y = rate.T.to_numpy()
    m = len(cols)
    base = -(y * (m - 0.5 - np.arange(m)[:, None])).sum(axis=0) / m
    lower = base + np.vstack([np.zeros(y.shape[1]), np.cumsum(y, axis=0)[:-1]])
    for i, (c_, col) in enumerate(zip(cols, palette)):
        j = int(np.argmax(y[i]))
        if y[i, j] < 0.05:                               # band too thin to carry a label
            continue
        ax.text(rate.index[j], lower[i, j] + y[i, j] / 2, c_, ha="center", va="center", fontsize=10, fontweight="bold",
                color="white" if c_ in ("brain rot", "tung tung", "skibidi") else "#222")
    ax.plot([pd.Timestamp("2022-02-01")] * 2, [-0.25, 0.25], color="#222", lw=3)
    ax.text(pd.Timestamp("2022-03-01"), 0, "0.5 hits per\n10,000 words", va="center", fontsize=9, color="#222")
    ax.set_xlim(full[0], full[-1])
    yr = p.groupby(p.index.year).sum().div(tok.groupby(tok.index.year).sum().reindex(p.groupby(p.index.year).sum().index), axis=0) * 1e4
    lead = {y: yr.loc[y].idxmax() for y in (2022, 2025)}
    finding_title(ax, f"Brainrot vocabulary peaked in {peak:%b %Y} ({tot[peak]:.2f} per 10,000 words); lead term: '{lead[2022]}' then '{lead[2025]}'",
                  "Stream graph: band thickness = hits per 10,000 words of each term (comments of all six subreddits, 3-month mean)")
    caption(fig, SAMPLE_NOTE + " Terms of the core and extended lexicon only; mewing, fanum tax and tralalero are too rare to show.")
    save(fig, "C15b_terms_by_year")
    return fig


# ---------------------------------------------------------------- monthly text metrics (MTLD, Flesch, VADER)
def _tm():
    t = load("text_metrics_monthly")
    return t


def _band_multiples(df, col, ylabel, fname, title, caption_txt, ylim=None, min_col=None, min_val=None):
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.8), sharex=True, sharey=True)
    for ax, s in zip(axes.flat, ORDER):
        d = df[df.subreddit == s].sort_values("month").dropna(subset=[col])
        if min_col:
            d = d[d[min_col] >= min_val]
        if d.empty:
            continue
        r = d[col].rolling(12, min_periods=6)
        ax.plot(d["month"], d[col], color=SUB_COLORS[s], lw=0.7, alpha=0.3)
        ax.fill_between(d["month"], r.quantile(0.25), r.quantile(0.75), color=SUB_COLORS[s], alpha=0.2, lw=0)
        ax.plot(d["month"], r.median(), color=SUB_COLORS[s], lw=2.2)
        ax.set_title(NAMES[s], fontsize=11, loc="left", color=SUB_COLORS[s])
        ax.xaxis.set_major_locator(mdates.YearLocator(6, month=1, day=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel)
    if ylim:
        axes[0, 0].set_ylim(*ylim)
    suptitle(fig, title(df), y=1.04)
    fig.tight_layout()
    caption(fig, caption_txt)
    save(fig, fname)
    return fig


def _period_change(df, col, a=(2012, 2014), b=(2024, 2026)):
    g = df.assign(y=df.month.dt.year)
    early = g[(g.y >= a[0]) & (g.y <= a[1])].groupby("subreddit")[col].median()
    late = g[(g.y >= b[0]) & (g.y <= b[1])].groupby("subreddit")[col].median()
    return early, late


def c11():
    """Small multiples: MTLD of a fixed 5,000-word random sample per subreddit-month; rolling median and middle-half band."""
    def title(df):
        e, l = _period_change(df, "mtld")
        return (f"Lexical diversity did not fall: MTLD in r/teenagers went from a median of {e['teenagers']:.0f} (2012-14) to {l['teenagers']:.0f} (2024-26), "
                f"r/memes {e['memes']:.0f} to {l['memes']:.0f}, r/books {e['books']:.0f} to {l['books']:.0f}")
    return _band_multiples(_tm(), "mtld", "MTLD", "C11_lexical_diversity_mtld", title,
                           "Source: Arctic Shift sample, comments. MTLD on a random sample of 5,000 words per subreddit-month (same size every month). "
                           "Bold = 12-month rolling median of the monthly values, band = middle half of those months. Short comments from many authors mix more words, so "
                           "MTLD of short-comment communities is not a measure of one writer's vocabulary.")


def c12():
    """Slope chart: median Flesch reading ease of comments with 10+ words, 2012-14 versus 2024-26."""
    t = _tm()
    e, l = _period_change(t, "flesch_median")
    fig, ax = plt.subplots(figsize=(7.5, 5.4))
    texts = []
    for s in ORDER:
        if pd.isna(e.get(s)) or pd.isna(l.get(s)):
            continue
        ax.plot([0, 1], [e[s], l[s]], "-o", color=SUB_COLORS[s], lw=2.4, ms=7, mec="white", mew=1.5)
        texts.append(ax.text(-0.04, e[s], f"{NAMES[s]}  {e[s]:.0f}", color=SUB_COLORS[s], ha="right", va="center", fontsize=11))
        texts.append(ax.text(1.04, l[s], f"{l[s]:.0f}  {NAMES[s]}", color=SUB_COLORS[s], ha="left", va="center", fontsize=11))
    ax.set_xlim(-0.75, 1.75)
    ax.set_xticks([0, 1], ["2012-14", "2024-26"])
    ax.set_ylabel("Flesch reading ease (higher = easier)")
    ax.grid(axis="x", alpha=0)
    ax.spines["left"].set_visible(False)
    ax.set_yticks([])
    d = (l - e).dropna()
    finding_title(ax, f"Readability barely moved: no subreddit shifted by more than {d.abs().max():.0f} points on a 100-point scale",
                  "Median Flesch reading ease of comments with 10+ words, by subreddit")
    adjust_text(texts, ax=ax, only_move={"text": "y"})
    caption(fig, "Source: Arctic Shift sample, up to 400 comments of 10+ words per subreddit-month. Flesch is built for full sentences; "
                 "chat-style comments without punctuation read as 'easy' by design.")
    save(fig, "C12_readability_slope")
    return fig


def c14():
    """Lines: emoji code points per 10,000 words per subreddit-month, 12-month mean."""
    e = load("emoji_monthly")
    e = e[(e.type == "comment") & (e.tokens >= 50_000)].copy()
    e = _roll(e, "per_10k_words")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for s in ORDER:
        d = e[e.subreddit == s].dropna(subset=["roll"])
        ax.plot(d["month"], d["roll"], color=SUB_COLORS[s], lw=2.2 if s in ("teenagers", "memes") else 1.4)
    last = e.groupby("subreddit")["roll"].last()
    pk = e.loc[e.groupby("subreddit")["roll"].idxmax()].set_index("subreddit")
    others = [s for s in ORDER if s not in ("teenagers", "memes")]
    hi = max(pk.loc[others, "roll"])
    t_end = e["month"].max() + pd.Timedelta(days=60)
    ax.text(t_end, last["teenagers"], "r/teenagers", color=SUB_COLORS["teenagers"], fontsize=11, va="center")
    ax.text(t_end, last["memes"], "r/memes", color=SUB_COLORS["memes"], fontsize=11, va="center")
    ax.annotate("books, explainlikeimfive,\ntodayilearned, nosurf:\nnever above " + f"{hi:.0f}", (pd.Timestamp("2022-01-01"), 8),
                xytext=(pd.Timestamp("2018-03-01"), 80), fontsize=10, color="#444", arrowprops=dict(arrowstyle="-", color="#999"))
    _xaxis(ax, 900)
    ax.set_ylabel("Emoji per 10,000 words (12-month mean)")
    ax.set_ylim(0, None)
    finding_title(ax, f"Emoji took off in the short-form communities: r/teenagers peaked at {pk.loc['teenagers', 'roll']:.0f} per 10,000 words "
                      f"({pk.loc['teenagers', 'month']:%b %Y}) and is at {last['teenagers']:.0f} now",
                  "Emoji code points per 10,000 words, comments, 12-month mean")
    caption(fig, "Source: Arctic Shift sample. Counts Unicode emoji/pictograph code points only (no text emoticons, flags and multi-part emoji count by part).")
    save(fig, "C14_emoji_per_10k_words")
    return fig


def c36():
    """Lines: mean VADER compound score per subreddit-month (up to 2,000 comments), 12-month mean."""
    t = _tm()
    t = t[t.vader_n >= 300].copy()
    t = _roll(t, "vader_mean")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    texts = _lines(ax, t)
    ax.set_ylabel("Mean VADER compound score (12-month mean)")
    ax.axhline(0, color="#999", lw=0.8)
    last = t.groupby("subreddit")["roll"].last()
    lo, hi = last.idxmin(), last.idxmax()
    finding_title(ax, f"Comments are least positive in {NAMES[lo]} ({last[lo]:+.2f}) and most positive in {NAMES[hi]} ({last[hi]:+.2f}) today",
                  "Mean VADER compound score of comments (-1 very negative, +1 very positive)")
    adjust_text(texts, ax=ax, only_move={"text": "y"})
    caption(fig, "Source: Arctic Shift sample, up to 2,000 comments per subreddit-month. VADER is a word-list method and misreads sarcasm "
                 "(common in r/memes); read changes in level, not single values.")
    save(fig, "C36_sentiment_over_time")
    return fig


# ---------------------------------------------------------------- C17 / C18: words and bigrams, early vs late
EARLY_LATE = "early period 2013-2016 vs late period 2023-2026"
GROUP_COLOR = {"short_form": "#d95f02", "long_form": "#1b9e77"}
GROUP_TITLE = {"short_form": "r/memes + r/teenagers", "long_form": "r/books + r/explainlikeimfive"}


def log_odds_z(counts, grp, a_prior=1000, min_total=150, drop_stop=True):
    """Weighted log-odds (Monroe et al. 2008, informative Dirichlet prior): positive z = more typical of the late period."""
    allc = counts.groupby("word")["n"].sum()
    prior = allc / allc.sum() * a_prior
    d = counts[counts.grp == grp].pivot_table(index="word", columns="period", values="n", aggfunc="sum").fillna(0)
    d = d[(d["early"] + d["late"]) >= min_total]
    if drop_stop:                                           # rank content words; the prior still uses all words
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
        stop = set(ENGLISH_STOP_WORDS) | {"i'm", "don't", "it's", "i've", "didn't", "that's", "doesn't", "can't", "you're", "isn't", "i'll",
                                           "they're", "i'd", "that's", "there's", "he's", "she's", "we're", "won't", "wasn't", "aren't"}
        d = d[~d.index.isin(stop)]
    a = prior.reindex(d.index).fillna(0.01)
    n_e, n_l = counts[(counts.grp == grp) & (counts.period == "early")]["n"].sum(), counts[(counts.grp == grp) & (counts.period == "late")]["n"].sum()
    ye, yl = d["early"], d["late"]
    delta = np.log((yl + a) / (n_l + a_prior - yl - a)) - np.log((ye + a) / (n_e + a_prior - ye - a))
    z = delta / np.sqrt(1 / (yl + a) + 1 / (ye + a))
    return pd.DataFrame({"z": z, "early": ye, "late": yl}).sort_values("z")


def c17(k=12):
    """Diverging bars: weighted log-odds z-scores of content words, 2013-16 versus 2023-26, short-form and long-form groups."""
    wc = load("word_counts_period")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))
    tops = {}
    for ax, g in zip(axes, ["short_form", "long_form"]):
        z = log_odds_z(wc, g)
        sel = pd.concat([z.head(k), z.tail(k)])
        tops[g] = (z.tail(3).index[::-1].tolist(), z.head(3).index.tolist())
        cols = [GRAY if v < 0 else GROUP_COLOR[g] for v in sel["z"]]
        ax.barh(range(len(sel)), sel["z"], color=cols, height=0.75)
        for i, (w, v) in enumerate(zip(sel.index, sel["z"])):
            ax.text(v + (1 if v >= 0 else -1), i, w, va="center", ha="left" if v >= 0 else "right", fontsize=10)
        ax.set_yticks([])
        ax.axvline(0, color="#444", lw=0.8)
        lim = max(abs(sel["z"])) * 1.45
        ax.set_xlim(-lim, lim)
        ax.set_xlabel("Weighted log-odds z-score")
        ax.grid(False)
        ax.grid(axis="x", alpha=0.25)
        ax.set_title(GROUP_TITLE[g], loc="left", fontsize=11, color=GROUP_COLOR[g])
        ax.text(0.02, 0.01, "more typical of 2013-16", transform=ax.transAxes, fontsize=9, color="#666")
        ax.text(0.98, 0.01, "more typical of 2023-26", transform=ax.transAxes, fontsize=9, color="#666", ha="right")
    gl, ge = tops["short_form"]
    suptitle(fig, f"Short-form talk moved from '{ge[0]}', '{ge[1]}' and '{ge[2]}' (2013-16) to '{gl[0]}', '{gl[1]}' and '{gl[2]}' (2023-26)",
             y=1.03)
    fig.tight_layout()
    caption(fig, "Source: Arctic Shift sample, comments, " + EARLY_LATE + ". Content words with 150+ uses (stop words not ranked), URLs and markup removed; "
                 "bars = z-score of the log-odds ratio with an informative prior (Monroe et al. 2008). A large |z| says the shift is not chance, not why it happened.")
    save(fig, "C17_words_gaining_losing")
    return fig


def c18(k=12, pool=40):
    """Bars: most frequent word pairs per group and period from a fixed random sample of 400,000 comments; colored if new in the top 40."""
    b = load("bigram_counts_period")
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    kept = {}
    for r, g in enumerate(["short_form", "long_form"]):
        top = {p: b[(b.grp == g) & (b.period == p)].nlargest(pool, "n") for p in ("early", "late")}
        kept[g] = len(set(top["late"].head(k)["bigram"]) & set(top["early"]["bigram"]))
        for c, p in enumerate(["early", "late"]):
            ax = axes[r, c]
            d = top[p].head(k).iloc[::-1]
            other = set(top["late" if p == "early" else "early"]["bigram"])
            new = ~d["bigram"].isin(other)
            ax.barh(range(len(d)), d["n"] / 400, color=[GROUP_COLOR[g] if x else "#c8c8c8" for x in new], height=0.72)
            for i, (w, v) in enumerate(zip(d["bigram"], d["n"] / 400)):
                ax.text(0.2, i, w, va="center", fontsize=10, color="#222")
            ax.set_yticks([])
            ax.grid(False)
            ax.grid(axis="x", alpha=0.25)
            ax.set_title(f"{GROUP_TITLE[g]}, {'2013-16' if p == 'early' else '2023-26'}", loc="left", fontsize=11, color=GROUP_COLOR[g])
            if r == 1:
                ax.set_xlabel("Occurrences per 1,000 comments")
    suptitle(fig, f"The most frequent word pairs hardly changed: {kept['short_form']} of the 12 most common pairs in r/memes + r/teenagers in 2023-26 "
                  f"were already in the 2013-16 top 40 ({kept['long_form']} of 12 in long-form)", y=1.01)
    fig.tight_layout()
    caption(fig, "Source: Arctic Shift, a fixed random sample of 400,000 comments per group and period, URLs and markup removed. Pairs containing a "
                 "stop word are excluded. Colored = not in the top 40 of the other period.")
    save(fig, "C18_bigrams_early_late")
    return fig
