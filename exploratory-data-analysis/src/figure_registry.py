"""One entry per figure: the function that draws it, the tables it reads and the step that builds them.

`python -c "from src.figure_registry import render_index; render_index()"` writes docs/figure_index.md;
`python run_pipeline.py figures` redraws every PNG in figures/ from the cached tables.
"""
import importlib
import inspect

from .config import ROOT

# table -> (function that builds it, run_pipeline step)
BUILDERS = {
    "processed Parquet (data/processed)": ("io_reddit.build_all", "clean"),
    "monthly_totals": ("aggregates.monthly_totals", "aggregates"),
    "sample_weights": ("aggregates.sample_weights", "aggregates"),
    "overview_counts": ("aggregates.overview_counts", "aggregates"),
    "raw_quality_monthly": ("aggregates.raw_quality_monthly", "aggregates"),
    "author_activity": ("aggregates.author_activity", "aggregates"),
    "length_hist": ("aggregates.length_hist", "aggregates"),
    "score_hist": ("aggregates.score_hist", "aggregates"),
    "score_by_length": ("aggregates.score_by_length", "aggregates"),
    "hour_dow": ("aggregates.hour_dow", "aggregates"),
    "daily_full_coverage": ("aggregates.daily_full_coverage", "aggregates"),
    "lexicon_monthly": ("textmining.lexicon_monthly (after build_matches)", "text"),
    "lexicon_terms_by_year": ("textmining.term_counts (after build_matches)", "text"),
    "lexicon_terms_by_month": ("textmining.term_counts (after build_matches)", "text"),
    "emoji_monthly": ("textmining.emoji_monthly", "text"),
    "text_metrics_monthly": ("textmining.text_metrics_monthly", "text"),
    "word_counts_period": ("textmining.words_period", "text"),
    "bigram_counts_period": ("textmining.words_period", "text"),
    "per-comment features (data/processed/derived)": ("textmining.build_features", "features"),
    "daily_features": ("events.build_daily", "events"),
    "event_effects": ("figs_crisis.effects_table", "events"),
    "wui_monthly": ("external.load_wui (downloads the World Uncertainty Index)", "validate"),
    "youtube_trending_monthly": ("external.trending_monthly (downloads the Kaggle files, about 800 MB, cached)", "external"),
}

# id, PNG name, module, function, question in the notebooks, input tables
FIGURES = [
    ("C01", "C01_records_per_month", "figs_overview", "c01", "Q1", ["monthly_totals"]),
    ("C02", "C02_subreddits_carrying_data", "figs_overview", "c02", "Q2", ["sample_weights"]),
    ("C03", "C03_nosurf_authors_per_month", "figs_overview", "c03", "Q3", ["overview_counts"]),
    ("C03b", "C03b_removed_and_bot_share", "figs_overview", "c03b", "Q3b", ["raw_quality_monthly"]),
    ("C04", "C04_author_concentration", "figs_overview", "c04", "Q4", ["author_activity"]),
    ("C05", "C05_comment_length_by_subreddit", "figs_overview", "c05", "Q5", ["length_hist"]),
    ("C06", "C06_hour_by_weekday", "figs_overview", "c06", "Q6", ["hour_dow"]),
    ("C07", "C07_comments_per_submission", "figs_overview", "c07", "Q7", ["monthly_totals"]),
    ("C08", "C08_score_distribution_and_length", "figs_overview", "c08", "Q8", ["score_hist", "score_by_length"]),
    ("C09", "C09_nosurf_daily_volume", "figs_overview", "c09", "Q9", ["daily_full_coverage"]),
    ("C10", "C10_median_comment_length", "figs_text", "c10", "Q10", ["overview_counts"]),
    ("C11", "C11_lexical_diversity_mtld", "figs_text", "c11", "Q12", ["text_metrics_monthly"]),
    ("C12", "C12_readability_slope", "figs_text", "c12", "Q13", ["text_metrics_monthly"]),
    ("C13", "C13_very_short_share", "figs_text", "c13", "Q11", ["overview_counts"]),
    ("C14", "C14_emoji_per_10k_words", "figs_text", "c14", "Q14", ["emoji_monthly"]),
    ("C15", "C15_brainrot_per_10k_words", "figs_text", "c15", "Q15", ["lexicon_monthly"]),
    ("C15b", "C15b_terms_by_year", "figs_text", "c15b", "Q15b", ["lexicon_terms_by_month", "overview_counts"]),
    ("C16", "C16_brainrot_reach", "figs_text", "c16", "Q16", ["lexicon_monthly"]),
    ("C17", "C17_words_gaining_losing", "figs_text", "c17", "Q17", ["word_counts_period"]),
    ("C18", "C18_bigrams_early_late", "figs_text", "c18", "Q18", ["bigram_counts_period"]),
    ("C36", "C36_sentiment_over_time", "figs_text", "c36", "Q36", ["text_metrics_monthly"]),
    ("C20", "C20_crisis_words_timeline", "figs_crisis", "c20", "Q20", ["daily_features"]),
    ("C20b", "C20b_event_attention", "figs_crisis", "c20b", "Q20b", ["daily_features", "event_effects"]),
    ("C21", "C21_event_study_sentiment", "figs_crisis", "c21", "Q21", ["daily_features"]),
    ("C22", "C22_event_study_doomscroll", "figs_crisis", "c22", "Q22", ["daily_features"]),
    ("C23", "C23_nosurf_rhythm_shift", "figs_crisis", "c23", "Q23", ["per-comment features (data/processed/derived)"]),
    ("C24", "C24_nosurf_session_length", "figs_crisis", "c24", "Q24", ["processed Parquet (data/processed)"]),
    ("C26", "C26_same_authors_before_after", "figs_crisis", "c26", "Q26", ["per-comment features (data/processed/derived)"]),
    ("C27", "C27_placebo_sentiment", "figs_crisis", "c27", "Q27", ["daily_features", "event_effects"]),
    ("C28", "C28_lead_lag_uncertainty", "figs_crisis", "c28", "Q28", ["daily_features", "wui_monthly"]),
    ("C29", "C29_sentiment_changepoints", "figs_crisis", "c29", "Q29", ["daily_features"]),
    ("C33", "C33_youtube_trending_brainrot", "figs_external", "c33", "Q33", ["youtube_trending_monthly"]),
    ("V01", "V01_missingness", "validate", "missingness_figure", "data section", ["processed Parquet (data/processed)"]),
]
BY_FN = {f[3]: f for f in FIGURES}


def _func(module, fn):
    return getattr(importlib.import_module(f"src.{module}"), fn)


def code_ref(fn):
    """Markdown line shown in the notebooks under every chart: where the code is and where its data comes from."""
    cid, png, module, fn, q, inputs = BY_FN[fn]
    lines = ", ".join(f"`{t}`" for t in inputs)
    steps = ", ".join(sorted({BUILDERS[t][1] for t in inputs}))
    return (f"**Code for {cid}:** `src/{module}.py` function `{fn}()`; reads {lines}; "
            f"built by `python run_pipeline.py {steps}`. All charts and tables: `docs/figure_index.md`, scripts explained in `docs/code_guide.md`.")


def render_index(path=None):
    rows = ["# Figure index: every chart and the code behind it\n",
            "Generated by `src/figure_registry.py`. Redraw all charts with `python run_pipeline.py figures`.\n",
            "| Figure | PNG | Drawn by | Question | Reads | Tables built by | What it shows |", "|---|---|---|---|---|---|---|"]
    for cid, png, module, fn, q, inputs in FIGURES:
        f = _func(module, fn)
        line = inspect.getsourcelines(f)[1]
        doc = (inspect.getdoc(f) or "").split("\n")[0]
        built = "; ".join(f"`{BUILDERS[t][0]}`" for t in inputs)
        rows.append(f"| {cid} | `figures/{png}.png` | `src/{module}.py:{line}` `{fn}()` | {q} | {', '.join(f'`{t}`' for t in inputs)} | {built} | {doc} |")
    path = path or ROOT / "docs" / "figure_index.md"
    path.write_text("\n".join(rows) + "\n")
    return path


def redraw_all():
    """Redraw every PNG from the cached tables (no notebooks needed)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .viz import set_style
    set_style()
    for cid, png, module, fn, q, inputs in FIGURES:
        out = _func(module, fn)()
        if isinstance(out, plt.Figure):
            plt.close(out)
        print("drew", cid, png)
