"""Phase 4 figures (H4: crises, negativity, doomscrolling proxies)."""
import duckdb
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl

from . import events as ev
from .config import AGG, EVENTS, PROC
from .external import load_wui
from .figs_overview import NAMES, ORDER, SAMPLE_NOTE, SHORT_EVENTS
from .sessions import sessions
from .viz import GRAY, GROUP_COLORS, SUB_COLORS, caption, finding_title, save, suptitle

GROUPS = {"short_form": ["memes", "teenagers"], "long_form": ["books", "explainlikeimfive"],
          "baseline": ["todayilearned"], "reflective": ["nosurf"]}
GROUP_LABEL = {"short_form": "r/memes + r/teenagers", "long_form": "r/books + r/explainlikeimfive",
               "baseline": "r/todayilearned", "reflective": "r/nosurf"}
EV_LABEL = {k: SHORT_EVENTS[k] for k in EVENTS}
H4_NOTE = ("Source: Arctic Shift sample. No news subreddits are in the data yet, so this tests only whether non-news communities react.")


def _daily():
    return ev.load_daily()


def _monthly_rate(daily, subs, num, den, scale=1e4):
    d = daily[daily.subreddit.isin(subs)].assign(month=lambda x: x.day.dt.to_period("M").dt.to_timestamp())
    g = d.groupby("month")[[num, den]].sum()
    return g[num] / g[den] * scale


# ---------------------------------------------------------------- C20
def c20():
    """Small multiples: crisis words per 10,000 words per month with the four event dates."""
    daily = _daily()
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.8), sharex=True, sharey=True)
    peaks, med = {}, {}
    for ax, s in zip(axes.flat, ORDER):
        d = daily[daily.subreddit == s].assign(month=lambda x: x.day.dt.to_period("M").dt.to_timestamp())
        g = d.groupby("month")[["hits_crisis", "tokens"]].sum()
        g = g[g.tokens >= 50_000]
        r = g["hits_crisis"] / g["tokens"] * 1e4
        sm = r.rolling(3, min_periods=1, center=True).mean()
        ax.plot(r.index, r, color=SUB_COLORS[s], lw=0.8, alpha=0.35)
        ax.plot(sm.index, sm, color=SUB_COLORS[s], lw=2.2)
        for k, v in EVENTS.items():
            ax.axvline(pd.Timestamp(v), color="black", lw=0.8, ls="--", alpha=0.6)
        ax.set_title(NAMES[s], fontsize=11, loc="left", color=SUB_COLORS[s])
        ax.xaxis.set_major_locator(mdates.YearLocator(6, month=1, day=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        peaks[s] = (sm.idxmax(), sm.max())
        med[s] = r.median()
    fig.supylabel("Crisis words per 10,000 words", fontsize=11)
    ax0 = axes[0, 0]
    for (k, v), y in zip(EVENTS.items(), (0.97, 0.89, 0.81, 0.73)):
        ax0.annotate(EV_LABEL[k], (pd.Timestamp(v), y), xycoords=("data", "axes fraction"), xytext=(3, 0), textcoords="offset points",
                     fontsize=8, va="top")
    m = peaks["memes"]
    suptitle(fig, f"Crisis talk is event-driven in r/memes ({m[1]:.0f} per 10,000 words in {m[0]:%b %Y}, {m[1] / med['memes']:.1f}x its median), "
                  f"but the other communities have no common peak", y=1.04)
    fig.tight_layout()
    caption(fig, SAMPLE_NOTE + " Crisis words: war, pandemic, covid, lockdown, invasion, Ukraine, Gaza, Hamas, Israel, Palestine, genocide, terror, "
                 "shooting, assassination, crisis, recession, famine, refugees, earthquake, hurricane. Months under 50,000 words dropped. "
                 "Dashed lines = the four events.")
    save(fig, "C20_crisis_words_timeline")
    return fig


def c20b():
    """Event study: weekly event-specific word rate around each event, four community groups (manipulation check)."""
    def title(store):
        t = effects_table_cached()
        t = t[t.outcome.isin(ev.EVENT_OUTCOME.values())]
        n_sig = int(((t.p < 0.05) & (t.effect > 0)).sum())
        return (f"Each event reached the communities: event words rose in {n_sig} of {len(t)} community-event pairs (p < 0.05 vs random dates); "
                f"r/todayilearned barely reacted to three of the four events", "Gray band = the four weeks used for the test. Change in event-specific words per 10,000 words vs the 8 weeks before.")
    return _panels(lambda n: ev.EVENT_OUTCOME[n], "Change in event words per 10,000 words\n(vs the 8 weeks before)", "C20b_event_attention", title,
                   note="Source: Arctic Shift sample. Event words: covid/pandemic/lockdown; Ukraine/Russia/Putin/invasion; Gaza/Hamas/Israel/Palestine; "
                        "Kirk/Turning Point/assassination. This checks that the event reached each community.")


# ---------------------------------------------------------------- C21 / C22 event-study panels
def _panels(outcome_for, ylabel, fname, title_fn, yfmt=None, groups=GROUPS, note=H4_NOTE, ylim=None):
    daily = _daily()
    dense = {g: ev.dense(daily, subs) for g, subs in groups.items()}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharey=ylim is not None)
    store = {}
    for ax, (name, date) in zip(axes.flat, EVENTS.items()):
        oc = outcome_for(name)
        for g in groups:
            c = ev.event_curve(dense[g], date, oc)
            store[(name, g)] = c
            ax.plot(c.index, c["delta"], color=GROUP_COLORS[g], lw=2.2, marker="o", ms=3)
        ax.axhline(0, color="#444", lw=0.8)
        ax.axvline(-0.5, color="black", lw=0.9, ls="--")
        ax.axvspan(-0.5, 3.5, color="#999", alpha=0.10, lw=0)
        ax.set_title(f"{name}  ({pd.Timestamp(date):%d %b %Y})", loc="left", fontsize=11)
        ax.set_xlabel("Weeks from the event")
        if ylim:
            ax.set_ylim(*ylim)
    fig.supylabel(ylabel, fontsize=11)
    title, info = title_fn(store)
    suptitle(fig, title, y=1.03)
    from matplotlib.lines import Line2D
    fig.legend([Line2D([0], [0], color=GROUP_COLORS[g], lw=2.5) for g in groups], [GROUP_LABEL[g] for g in groups],
               loc="lower center", ncol=4, frameon=False, fontsize=10, bbox_to_anchor=(0.5, -0.03))
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    caption(fig, note + " " + info)
    save(fig, fname)
    return fig


def c21():
    """Event study: weekly mean VADER compound around each event as change versus the 8 weeks before, four community groups."""
    def title(store):
        eff = {k: v["delta"].loc[0:3].mean() for k, v in store.items()}
        ukr = [eff[(n, g)] for (n, g) in eff if n.startswith(("Russia", "Hamas", "Assassination"))]
        share_neg = np.mean([e < 0 for e in ukr])
        return (f"After the three violent events the tone dipped in {share_neg * 12:.0f} of 12 community-event pairs, "
                f"but by no more than {abs(min(eff.values())):.2f} compound points", "Gray band = the four weeks used for the test. Change in mean VADER compound score vs the 8 weeks before.")
    return _panels(lambda n: "sentiment", "Change in mean VADER compound", "C21_event_study_sentiment", title)


def c22():
    """Event study: weekly doomscroll mentions per 10,000 words around each event, r/nosurf versus the other five subreddits."""
    daily = _daily()
    groups = {"reflective": ["nosurf"], "other": ["memes", "teenagers", "books", "explainlikeimfive", "todayilearned"]}
    GROUP_COLORS["other"] = GRAY
    GROUP_LABEL["other"] = "other five subreddits"

    def title(store):
        d = ev.dense(daily, ["nosurf"])
        eff = {n: ev.real_effect(d, dt, "doom_rate") for n, dt in EVENTS.items()}
        pv = {n: ev.placebo_p(eff[n], ev.placebo(d, "doom_rate", EVENTS.values(), n=400)) for n in EVENTS}
        k = max(eff, key=lambda x: abs(eff[x]))
        base = ev.ratio(d, "doom_rate", 0, len(d) - 1)
        return (f"'Doomscrolling' talk in r/nosurf (about {base:.1f} per 10,000 words) moved by less than 1 at every event; only the "
                f"{EV_LABEL[k]} stands out ({eff[k]:+.1f}, p = {pv[k]:.2f})", "Weekly 'doomscroll*' mentions per 10,000 words, change vs the 8 weeks before. Only r/nosurf uses the word often.")
    return _panels(lambda n: "doom_rate", "Change in doomscroll mentions per 10,000 words", "C22_event_study_doomscroll", title,
                   groups=groups, note="Source: Arctic Shift, comments. A mention is a proxy for talk about doomscrolling, not for doing it.")


# ---------------------------------------------------------------- C27 placebo
def effects_table(n=400):
    """Post-minus-pre effects at the four events and placebo p-values, per group and outcome."""
    daily = _daily()
    rows = []
    for g, subs in GROUPS.items():
        d = ev.dense(daily, subs)
        for name, date in EVENTS.items():
            for oc in ("sentiment", "neg_share", EVENT_OUTCOME_OF(name), "crisis_rate"):
                real = ev.real_effect(d, date, oc)
                fake = ev.placebo(d, oc, EVENTS.values(), n=n)
                rows.append(dict(group=g, event=name, outcome=oc, effect=real, placebo_sd=np.nanstd(fake),
                                 p=ev.placebo_p(real, fake), placebo_lo=np.nanpercentile(fake, 2.5), placebo_hi=np.nanpercentile(fake, 97.5)))
    df = pd.DataFrame(rows)
    df.to_parquet(AGG / "event_effects.parquet", index=False)
    return df


def EVENT_OUTCOME_OF(name):
    return ev.EVENT_OUTCOME[name]


def c27(n=400):
    """Histograms: change in mean tone at 400 random fake dates with the real event marked (short-form and r/nosurf)."""
    daily = _daily()
    fig, axes = plt.subplots(2, 4, figsize=(12, 5.6), sharey="row")
    for r, g in enumerate(["short_form", "reflective"]):
        d = ev.dense(daily, GROUPS[g])
        for c, (name, date) in enumerate(EVENTS.items()):
            ax = axes[r, c]
            fake = ev.placebo(d, "sentiment", EVENTS.values(), n=n)
            real = ev.real_effect(d, date, "sentiment")
            p = ev.placebo_p(real, fake)
            ax.hist(fake, bins=30, color=GRAY, alpha=0.8)
            ax.axvline(real, color=GROUP_COLORS[g], lw=3)
            ax.set_title(f"{EV_LABEL[name]}: p = {p:.2f}", loc="left", fontsize=10, color=GROUP_COLORS[g] if p < 0.05 else "#222")
            ax.set_xlabel("Change in mean VADER compound")
            if c == 0:
                ax.set_ylabel(f"{GROUP_LABEL[g]}\nfake dates")
    sig = effects_table_cached()
    s = sig[(sig.outcome == "sentiment")]
    suptitle(fig, f"Is the dip real? {int((s.p < 0.05).sum())} of {len(s)} community-event tests fall outside the range of random dates "
                  f"({0.05 * len(s):.1f} expected by chance alone; the tests are not independent)", y=1.04)
    fig.tight_layout()
    caption(fig, "Gray = the same 4-weeks-after minus 8-weeks-before change at 400 random fake dates (never within 120 days of a real event); "
                 "colored line = the real event; p = share of fake dates with an equal or larger absolute change. " + SAMPLE_NOTE)
    save(fig, "C27_placebo_sentiment")
    return fig


def effects_table_cached():
    p = AGG / "event_effects.parquet"
    return pd.read_parquet(p) if p.exists() else effects_table()


# ---------------------------------------------------------------- C29 change-points
def c29():
    """Change-points (PELT) in monthly mean VADER per subreddit, with the four event dates."""
    daily = _daily()
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.8), sharex=True)
    n_near = 0
    n_total = 0
    for ax, s in zip(axes.flat, ORDER):
        r = _monthly_rate(daily, [s], "sum_compound", "n", scale=1)
        r = r[r.index >= "2013-01-01"] if s != "nosurf" else r[r.index >= "2016-01-01"]
        bks = ev.changepoints(r)
        ax.plot(r.index, r, color=SUB_COLORS[s], lw=1.2, alpha=0.8)
        edges = [r.index[0]] + bks + [r.index[-1] + pd.offsets.MonthBegin(1)]
        for a, b in zip(edges[:-1], edges[1:]):
            seg = r[(r.index >= a) & (r.index < b)]
            ax.plot([a, b], [seg.mean()] * 2, color="#222", lw=2)
        for b in bks:
            ax.axvline(b, color=SUB_COLORS[s], lw=1.2, ls=":")
        for k, v in EVENTS.items():
            ax.axvline(pd.Timestamp(v), color="black", lw=0.8, ls="--", alpha=0.5)
        for b in bks:
            n_total += 1
            n_near += any(abs((b - pd.Timestamp(v)).days) <= 92 for v in EVENTS.values())
        ax.set_title(f"{NAMES[s]} ({len(bks)} shifts)", fontsize=11, loc="left", color=SUB_COLORS[s])
        ax.xaxis.set_major_locator(mdates.YearLocator(6, month=1, day=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in axes[:, 0]:
        ax.set_ylabel("Mean VADER compound")
    chance = n_total * 4 * 7 / 160           # four +/-3-month windows (7 months each) among about 160 months
    suptitle(fig, f"Sentiment shifts rarely line up with the events: {n_near} of {n_total} detected change-points fall within 3 months of one "
                  f"(chance alone: about {chance:.1f})", y=1.04)
    fig.tight_layout()
    caption(fig, SAMPLE_NOTE + " Monthly mean VADER; black steps = mean between change-points (PELT, least squares, penalty from month-to-month noise); "
                 "dotted = change-point, dashed = event.")
    save(fig, "C29_sentiment_changepoints")
    return fig


# ---------------------------------------------------------------- C28 lead-lag with the World Uncertainty Index
def c28(max_lag=6):
    """Cross-correlation bars: monthly changes in the World Uncertainty Index versus tone and crisis words, lags -6 to +6 months."""
    daily = _daily()
    w = load_wui().set_index("month")["wui_global"]
    fig, axes = plt.subplots(2, 4, figsize=(12, 5.6), sharey="row", sharex=True)
    best = {}
    for c, (g, subs) in enumerate(GROUPS.items()):
        sent = _monthly_rate(daily, subs, "sum_compound", "n", scale=1)
        crisis = _monthly_rate(daily, subs, "hits_crisis", "tokens")
        for r, (y, label) in enumerate(((sent, "sentiment"), (crisis, "crisis words"))):
            df = pd.concat([w.rename("wui"), y.rename("y")], axis=1).dropna()
            df = df[df.index >= "2013-01-01"]
            d = df.diff().dropna()                           # month-to-month changes: removes the shared long trend
            lags = range(-max_lag, max_lag + 1)
            cc = [d["wui"].corr(d["y"].shift(-k)) for k in lags]     # k > 0: uncertainty comes first
            ax = axes[r, c]
            ax.bar(list(lags), cc, color=GROUP_COLORS[g], width=0.75)
            band = 1.96 / np.sqrt(len(d))
            ax.axhspan(-band, band, color="#999", alpha=0.2, lw=0)
            ax.axhline(0, color="#444", lw=0.8)
            if r == 0:
                ax.set_title(GROUP_LABEL[g], loc="left", fontsize=10, color=GROUP_COLORS[g])
            best[(g, label)] = (list(lags)[int(np.nanargmax(np.abs(cc)))], max(cc, key=abs))
            if c == 0:
                ax.set_ylabel(f"r ({label})")
    allr = [abs(v[1]) for v in best.values()]
    suptitle(fig, f"No lead or lag: month-to-month changes in global uncertainty are unrelated to changes in sentiment or crisis words "
                  f"in any community (largest |r| = {max(allr):.2f}, noise band +/-{band:.2f})", y=1.04)
    fig.supxlabel("Lag in months (positive = uncertainty comes first)", fontsize=11)
    fig.tight_layout()
    caption(fig, "Source: World Uncertainty Index (global GDP-weighted average, monthly, Ahir, Bloom and Furceri) and Arctic Shift sample. "
                 "Both series are first-differenced. Gray band = approximate 95% range for no relation. Monthly values, 2013-2026.")
    save(fig, "C28_lead_lag_uncertainty")
    return fig


# ---------------------------------------------------------------- nosurf windows: C23, C24, C26
PRE, POST = 56, 28


def _nosurf_comments():
    return duckdb.sql(f"""
        SELECT f.id, f.ts, f.compound, p.author_id FROM read_parquet('{PROC}/derived/features_nosurf.parquet') f
        JOIN read_parquet('{PROC}/comment_nosurf.parquet') p USING (id)""").df()


def _smooth_h(a):
    return (np.roll(a, 1, 1) + a + np.roll(a, -1, 1)) / 3


def _share_matrix(ts):
    m = np.zeros((7, 24))
    for dow, hr in zip(ts.dt.dayofweek.to_numpy(), ts.dt.hour.to_numpy()):
        m[dow, hr] += 1
    return _smooth_h(m / m.sum() * 100)


def c23(n_fake=150):
    """Heatmaps: change in r/nosurf's UTC weekday-by-hour comment share, 4 weeks after minus 8 weeks before each event."""
    df = _nosurf_comments()
    ts = df["ts"]
    rng = np.random.default_rng(42)
    real = [pd.Timestamp(v) for v in EVENTS.values()]
    days = pd.date_range("2018-01-01", "2026-07-15")
    ok = [d for d in days if all(abs((d - r).days) > 120 for r in real)]
    maxd = []
    for d in rng.choice(len(ok), n_fake, replace=False):
        t0 = ok[d]
        a = _share_matrix(ts[(ts >= t0 - pd.Timedelta(days=PRE)) & (ts < t0)])
        b = _share_matrix(ts[(ts >= t0) & (ts < t0 + pd.Timedelta(days=POST))])
        maxd.append(np.abs(b - a).max())
    ref = np.percentile(maxd, 95)
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.2), sharex=True, sharey=True)
    lim = 0
    mats = {}
    for name, date in EVENTS.items():
        t0 = pd.Timestamp(date)
        a = _share_matrix(ts[(ts >= t0 - pd.Timedelta(days=PRE)) & (ts < t0)])
        b = _share_matrix(ts[(ts >= t0) & (ts < t0 + pd.Timedelta(days=POST))])
        mats[name] = b - a
        lim = max(lim, np.abs(b - a).max())
    lim = max(lim, ref)
    for ax, (name, m) in zip(axes.flat, mats.items()):
        im = ax.imshow(m, cmap="PuOr", vmin=-lim, vmax=lim, aspect="auto")
        ax.set_title(f"{EV_LABEL[name]}: largest cell {np.abs(m).max():.2f} pp", loc="left", fontsize=10)
        ax.grid(False)
        ax.set_yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        ax.set_xticks([0, 6, 12, 18, 23])
    for ax in axes[1]:
        ax.set_xlabel("Hour of day (UTC)")
    n_over = sum(np.abs(m).max() > ref for m in mats.values())
    suptitle(fig, f"r/nosurf's daily rhythm did not shift: {n_over} of 4 events move any hour-by-weekday cell more than a random date does (95% of fake dates stay under {ref:.2f} pp)", y=1.04)
    fig.tight_layout(rect=(0, 0, 0.9, 1))
    cax = fig.add_axes([0.92, 0.18, 0.015, 0.62])
    fig.colorbar(im, cax=cax, label="Share of comments, 4 weeks after minus 8 weeks before (pp)")
    caption(fig, "Source: Arctic Shift, r/nosurf comments (complete). Shares per cell, smoothed over 3 hours. Purple = more after, orange = less after. "
                 "Reference range from 150 random fake dates.")
    save(fig, "C23_nosurf_rhythm_shift")
    return fig


def _sessions_nosurf():
    lf = pl.concat([pl.scan_parquet(PROC / "comment_nosurf.parquet").select("author_id", "ts"),
                    pl.scan_parquet(PROC / "submission_nosurf.parquet").select("author_id", "ts")])
    return sessions(lf).collect().to_pandas()


def c24():
    """ECDFs: length of gap-based posting sessions (2+ messages) in r/nosurf, 8 weeks before versus 4 weeks after each event."""
    s = _sessions_nosurf()
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.2), sharex=True, sharey=True)
    stats = {}
    for ax, (name, date) in zip(axes.flat, EVENTS.items()):
        t0 = pd.Timestamp(date)
        pre = s[(s.start >= t0 - pd.Timedelta(days=PRE)) & (s.start < t0)]
        post = s[(s.start >= t0) & (s.start < t0 + pd.Timedelta(days=POST))]
        for d, col, lab in ((pre, GRAY, "8 weeks before"), (post, SUB_COLORS["nosurf"], "4 weeks after")):
            m = d[d.n_msgs >= 2]["minutes"].clip(lower=1).sort_values().to_numpy()
            ax.plot(m, np.arange(1, len(m) + 1) / len(m), color=col, lw=2.2, label=lab)
        stats[name] = (pre[pre.n_msgs >= 2].minutes.median(), post[post.n_msgs >= 2].minutes.median(),
                       (pre.n_msgs >= 2).mean(), (post.n_msgs >= 2).mean(), len(pre), len(post))
        ax.set_xscale("log")
        ax.set_title(f"{EV_LABEL[name]}: median {stats[name][0]:.0f} to {stats[name][1]:.0f} min", loc="left", fontsize=10)
        ax.set_xlabel("Session length in minutes (log scale)")
        ax.grid(axis="x", alpha=0.25)
    axes[0, 0].legend(frameon=False, loc="lower right", fontsize=9)
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of sessions up to this length")
    med = [v[1] - v[0] for v in stats.values()]
    suptitle(fig, f"Posting sessions in r/nosurf barely changed around events: median length moved by {min(med):+.0f} to {max(med):+.0f} minutes", y=1.04)
    fig.tight_layout()
    caption(fig, "Source: Arctic Shift, r/nosurf comments and submissions (complete). Session = messages by one author with gaps of at most 30 minutes; "
                 "sessions of 2+ messages only. Reading without posting (lurking) is invisible here, so this is a proxy for active use only.")
    save(fig, "C24_nosurf_session_length")
    return fig


def c26(n_boot=500, n_fake=120):
    """Dot and interval: change in mean VADER of the same r/nosurf authors across each event, with a placebo band from random dates."""
    df = _nosurf_comments()
    df = df[df.author_id.notna()]
    rng = np.random.default_rng(42)

    def change(t0):
        pre = df[(df.ts >= t0 - pd.Timedelta(days=PRE)) & (df.ts < t0)].groupby("author_id").compound.mean()
        post = df[(df.ts >= t0) & (df.ts < t0 + pd.Timedelta(days=POST))].groupby("author_id").compound.mean()
        both = pre.index.intersection(post.index)
        return (post[both] - pre[both]).to_numpy()

    real = [pd.Timestamp(v) for v in EVENTS.values()]
    days = pd.date_range("2018-01-01", "2026-07-15")
    ok = [d for d in days if all(abs((d - r).days) > 120 for r in real)]
    fake = np.array([change(ok[i]).mean() for i in rng.choice(len(ok), n_fake, replace=False)])
    lo_f, hi_f = np.percentile(fake, [2.5, 97.5])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    names = list(EVENTS)
    ys = np.arange(len(names))[::-1]
    out = []
    ax.axvspan(lo_f, hi_f, color="#999", alpha=0.2, lw=0)
    ax.axvline(0, color="#444", lw=0.8)
    for y, name in zip(ys, names):
        diff = change(pd.Timestamp(EVENTS[name]))
        boots = [rng.choice(diff, len(diff)).mean() for _ in range(n_boot)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out.append((name, len(diff), diff.mean(), lo, hi))
        ax.plot([lo, hi], [y, y], color=SUB_COLORS["nosurf"], lw=2.5)
        ax.scatter([diff.mean()], [y], color=SUB_COLORS["nosurf"], s=80, zorder=3, edgecolor="white", linewidth=1.5)
        ax.text(hi + 0.006, y, f"{diff.mean():+.3f}, n = {len(diff)} authors" + ("  (outside the random-date range)" if diff.mean() < lo_f or diff.mean() > hi_f else ""),
                va="center", fontsize=9.5)
    ax.set_yticks(ys, [EV_LABEL[n] for n in names])
    ax.set_xlabel("Change in mean VADER compound of the same authors, 4 weeks after vs 8 weeks before")
    ax.grid(axis="y", alpha=0)
    ax.grid(axis="x", alpha=0.25)
    ax.set_xlim(min(lo_f, min(o[3] for o in out)) - 0.01, 0.17)
    n_out = sum(o[2] < lo_f or o[2] > hi_f for o in out)
    finding_title(ax, f"The same r/nosurf authors wrote less positively after all four events ({min(o[2] for o in out):+.2f} to {max(o[2] for o in out):+.2f}); "
                      f"{n_out} of 4 fall outside random dates",
                  "Authors who posted in both windows; dot = mean change, line = 95% bootstrap interval over authors, gray band = 95% of random fake dates")
    caption(fig, "Source: Arctic Shift, r/nosurf comments (complete). Each author counts once; fake dates are 120 random dates at least 120 days from any event. "
                 "Following the same authors removes the effect of who is writing, but not of the topic of the week.")
    save(fig, "C26_same_authors_before_after")
    return fig
