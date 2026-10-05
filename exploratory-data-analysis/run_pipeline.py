# python run_pipeline.py [step ...], all steps ~10 min
# order: clean aggregates text features events validate csv index checks
# external = opt-in, ~800 MB kaggle download
import sys
import warnings

warnings.filterwarnings("ignore")


def main(steps):
    from src import aggregates as ag, checks, events as ev, export, external, figure_registry, io_reddit, textmining as tm, validate
    if "clean" in steps:
        io_reddit.build_all()
        r = validate.reconcile()
        assert r.ok.all(), r
        validate.SCHEMA.validate(validate.sample(), lazy=True)
    if "aggregates" in steps:
        ag.build_phase2()
        ag.raw_quality_monthly()
    if "text" in steps:
        tm.build_matches()
        tm.lexicon_monthly()
        tm.term_counts()
        tm.emoji_monthly()
        tm.text_metrics_monthly()
        tm.words_period()
    if "features" in steps:  # ~4 min
        tm.build_features()
    if "events" in steps:
        ev.build_daily()
        ev.effects_table()
    if "validate" in steps:
        validate.vader_label_sample()
        external.load_wui()
    if "external" in steps:  # kaggle, cached by kagglehub
        external.trending_monthly()
    if "csv" in steps:
        export.build_csv()
    if "index" in steps:
        figure_registry.render_index()
    if "checks" in steps:
        checks.main()


if __name__ == "__main__":  # main guard: multiprocessing
    ALL = ["clean", "aggregates", "text", "features", "events", "validate", "csv", "index", "checks"]
    main(sys.argv[1:] or ALL)
