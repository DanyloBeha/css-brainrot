# Code guide: every script, what it does, what it reads and writes

Rule: every script that touched the data or drew a chart is in this repository. Nothing was run from a scratch file.
Every chart has a row in [figure_index.md](figure_index.md) (function, input tables, the step that builds them), a docstring
that says what it shows, and a "Code and data" line under it in the notebooks. Every number in the notebook text that is not
in a chart title is reproduced by `src/checks.py` (output in [numbers_checked.md](numbers_checked.md)).

```
data/reddit_arctic (raw, read-only)
   │  clean            src/io_reddit.py
   ▼
data/processed/*.parquet  (cleaned rows, common schema)          data/aggregates/cleaning_counts.parquet
   │  aggregates       src/aggregates.py          ──►  data/aggregates/*.parquet (small tables)
   │  text             src/textmining.py          ──►  lexicon, emoji, MTLD/Flesch/VADER, word and bigram tables
   │  features         src/textmining.build_features ► data/processed/derived/features_*.parquet (per-comment VADER, crisis words)
   │  events           src/events.py (incl. effects_table) ► daily_features, event_effects
   ▼
the H4 charts are drawn by code cells inside eda.ipynb (H4 section); nothing is saved to disk
```

`python run_pipeline.py` runs the whole chain (about 10 minutes); `python run_pipeline.py index` only rewrites `docs/figure_index.md`.

## `src/` (all logic)

| File | What it does | Reads | Writes |
| --- | --- | --- | --- |
| `config.py` | Paths, subreddit groups, the four verified event dates, seed | | |
| `io_reddit.py` | Raw Parquet to one cleaned Parquet per type and subreddit: common schema (comments and submissions), the cleaning rules in order (bots, moderator messages, templated text, empty or removed, spam, duplicate ids), hashed authors, UTC timestamps, word count per row. Prints and stores the row counts after every rule | `data/reddit_arctic/` | `data/processed/*.parquet`, `aggregates/cleaning_counts.parquet` |
| `lexicons.py` | The one tokenizer (lower case, curly apostrophes straightened, URLs removed), brainrot / sigma / doomscroll lexicons, event and crisis word lists | | |
| `validate.py` | pandera schema, reconciliation of row counts with the raw files, the 100-comment sample for hand-labeling VADER | processed | `processed/derived/vader_validation_sample.csv` |
| `aggregates.py` | Small tables behind the Phase 2 charts: exact monthly totals, sampling weights (monthly total / sampled rows), overview counts, length and score histograms, hour-by-weekday counts, author activity, daily counts for complete months, raw quality shares | processed, raw totals | `data/aggregates/*.parquet` |
| `textmining.py` | Lexicon matches and monthly rates per 10,000 words (and reach), emoji rates, MTLD on fixed 5,000-word samples, Flesch, VADER per month, word and bigram counts early vs late, per-comment features for H4, daily counts of every brainrot term (`lexicon_terms_daily`, behind C23 and C37) | processed | `data/aggregates/*.parquet`, `processed/derived/` |
| `events.py` | H4 machinery: daily table, ratio-of-sums effect for a pre/post window, event curves, placebo test at random dates, `effects_table` (all events, groups and outcomes), `term_event_effects` (brainrot terms around events), r/nosurf sessions and length buckets (`session_stats`), same-author tone changes (`authors_stats`), change-points (PELT) | `features_*.parquet` | `aggregates/daily_features.parquet` |
| `sessions.py` | Gap-based sessions (30-minute gap) from posting times | processed | |
| `external.py` | World Uncertainty Index download and monthly extract; YouTube trending (Kaggle rsrishav 2020-24 and keshavbansal95 2024-25): size-capped single-file downloads (`download_capped`), one row per unique video, brainrot and Roblox-game flags from title and tags, monthly counts and views | the web | `data/external/wui_monthly.parquet`, `youtube_trending_monthly.parquet`; Kaggle files stay in the kagglehub cache (outside the repo) |
| `export.py` | The CSV deliverable: one row per subreddit-month, no empty cells | aggregates | `outputs/3_FightClub_draft.csv` |
| `wordtracker.py` | **Universal word tracker**: any words or phrases (`*` = any ending, a space matches spaces and hyphens) to rate per 10,000 words and reach, per subreddit and month or year, same tokenizer and denominator as everywhere. `python -m src.wordtracker "doomscroll*" "six seven" --by year` | processed, overview_counts | prints or returns a table |
| H4 charts (C20, C20b, C21, C22, C23, C24, C26) | **No module: the drawing code is in the code cells of the H4 section of `eda.ipynb`**, next to each chart: a cell with the imports, a cell with the style (Jost fonts from `fonts/`, colours, caps title, legend box, event chips, save), then one cell per chart that draws it and prints its finding and a how-to-read line. The data preparation they call is in `events.py`, `textmining.py` and `sessions.py`. C27, C28, C29, C37 and the first C23 were removed from the report; the logic behind their numbers stays in `events.py` and `checks.py` | daily_features, event_effects, lexicon_terms_by_month, r/nosurf rows | `figures/` (saved by the cell) |
| (removed 2026-10-05) | The chart modules of the other sections (`figs_overview`, `figs_text`, `figs_external`, `viz`), notebooks 01, 02 and 04, `tools/` (notebook builders, `assemble_eda.py`, `insert_h4.py`) and `figures/` were deleted: only the H4 charts remain and they live in `eda.ipynb`. Everything is in git history (commit `1850a5d` and earlier) | | |
| `figure_registry.py` | Map of the H4 charts to the tables they read and the steps that build them; writes `docs/figure_index.md` | | `docs/figure_index.md` |
| `checks.py` | Raw profile, YouTube trending profile, repeated-text and spam look-ups, spike-day analysis, lexicon spot check, and every number quoted in the H4 section of `eda.ipynb` (event effects, doomscroll trend, brainrot terms and spike months, volume, sessions, authors, rhythm, change-points) | all | `docs/numbers_checked.md` |

## Other scripts

| File | What it does |
| --- | --- |
| `run_pipeline.py` | Runs the steps above in order (`clean aggregates text features events validate csv index checks`) |
| `../dataset-collection/*.py` | HW2: download (`arctic_download.py`), extraction (`extract_subreddits.py`), cleaning of the survey data (`clean_dataset.py`) |

## What is not committed
Row-level text (comments, titles) stays local: `data/processed/` (including `derived/`) and `data/reddit_arctic/` are in `.gitignore`.
The functions in `checks.py` that print comment or thread text (`repeated_texts`, `spam_candidates`, `lexicon_spot_check`, the titles in
`spike_context`) print to the terminal only. Everything a chart reads is a small aggregate in `data/aggregates/`, which is committed,
so the charts and notebooks can be re-run without the raw data.
