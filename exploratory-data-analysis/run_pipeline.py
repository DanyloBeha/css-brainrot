"""Rebuild every derived table from the raw Parquet in data/reddit_arctic/.

    python run_pipeline.py                 # all steps (about 10 minutes)
    python run_pipeline.py clean aggregates   # selected steps

Opt-in step (downloads about 800 MB from Kaggle once): python run_pipeline.py external
Steps, in order: clean -> aggregates -> text -> features -> events -> validate -> csv -> figures -> checks
"""
import sys
import warnings

warnings.filterwarnings("ignore")


def main(steps):
    from src import aggregates as ag, checks, events as ev, export, external, figs_crisis, figure_registry, io_reddit, textmining as tm, validate
    if "clean" in steps:                      # raw -> data/processed (common schema, cleaning rules, counts)
        io_reddit.build_all()
        r = validate.reconcile()
        assert r.ok.all(), r
        validate.SCHEMA.validate(validate.sample(), lazy=True)
    if "aggregates" in steps:                 # small tables for Phase 2 charts
        ag.build_phase2()
        ag.raw_quality_monthly()
    if "text" in steps:                       # lexicon matches, emoji, MTLD / Flesch / VADER, word counts
        tm.build_matches()
        tm.lexicon_monthly()
        tm.term_counts()
        tm.emoji_monthly()
        tm.text_metrics_monthly()
        tm.words_period()
    if "features" in steps:                   # per-comment VADER and crisis-word hits (about 4 minutes)
        tm.build_features()
    if "events" in steps:                     # daily table and event-study effects with placebo p-values
        ev.build_daily()
        figs_crisis.effects_table()
    if "validate" in steps:                   # V01 missingness chart, hand-label sample for VADER, World Uncertainty Index download
        validate.missingness_figure()
        validate.vader_label_sample()
        external.load_wui()
    if "external" in steps:                   # YouTube trending monthly table (Kaggle downloads, cached by kagglehub)
        external.trending_monthly()
    if "csv" in steps:
        export.build_csv()
    if "figures" in steps:                    # redraw every PNG in figures/ and rewrite docs/figure_index.md
        figure_registry.redraw_all()
        figure_registry.render_index()
    if "checks" in steps:                     # numbers quoted in the notebook text -> docs/numbers_checked.md
        checks.main()


if __name__ == "__main__":                    # the guard is needed: some steps use multiprocessing
    ALL = ["clean", "aggregates", "text", "features", "events", "validate", "csv", "figures", "checks"]
    main(sys.argv[1:] or ALL)
