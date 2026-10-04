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
   │  events           src/events.py + figs_crisis.effects_table ► daily_features, event_effects
   ▼
src/figs_*.py draw the charts (figures/*.png)  ──►  notebooks/*.ipynb  ──►  H4 block of eda.ipynb (tools/insert_h4.py)
```

`python run_pipeline.py` runs the whole chain (about 10 minutes); `python run_pipeline.py figures` redraws only the charts.

## `src/` (all logic)

| File | What it does | Reads | Writes |
| --- | --- | --- | --- |
| `config.py` | Paths, subreddit groups, the four verified event dates, seed | | |
| `io_reddit.py` | Raw Parquet to one cleaned Parquet per type and subreddit: common schema (comments and submissions), the cleaning rules in order (bots, moderator messages, templated text, empty or removed, spam, duplicate ids), hashed authors, UTC timestamps, word count per row. Prints and stores the row counts after every rule | `data/reddit_arctic/` | `data/processed/*.parquet`, `aggregates/cleaning_counts.parquet` |
| `lexicons.py` | The one tokenizer (lower case, curly apostrophes straightened, URLs removed), brainrot / sigma / doomscroll lexicons, event and crisis word lists | | |
| `validate.py` | pandera schema, reconciliation of row counts with the raw files, the V01 missingness chart, the 100-comment sample for hand-labeling VADER | processed | `figures/V01_missingness.png`, `processed/derived/vader_validation_sample.csv` |
| `aggregates.py` | Small tables behind the Phase 2 charts: exact monthly totals, sampling weights (monthly total / sampled rows), overview counts, length and score histograms, hour-by-weekday counts, author activity, daily counts for complete months, raw quality shares | processed, raw totals | `data/aggregates/*.parquet` |
| `textmining.py` | Lexicon matches and monthly rates per 10,000 words (and reach), emoji rates, MTLD on fixed 5,000-word samples, Flesch, VADER per month, word and bigram counts early vs late, per-comment features for H4 | processed | `data/aggregates/*.parquet`, `processed/derived/` |
| `events.py` | H4 machinery: daily table, ratio-of-sums effect for a pre/post window, event curves, placebo test at random dates, change-points (PELT) | `features_*.parquet` | `aggregates/daily_features.parquet` |
| `sessions.py` | Gap-based sessions (30-minute gap) from posting times | processed | |
| `external.py` | World Uncertainty Index download and monthly extract; YouTube trending (Kaggle rsrishav 2020-24 and keshavbansal95 2024-25): size-capped single-file downloads (`download_capped`), one row per unique video, brainrot and Roblox-game flags from title and tags, monthly counts and views | the web | `data/external/wui_monthly.parquet`, `youtube_trending_monthly.parquet`; Kaggle files stay in the kagglehub cache (outside the repo) |
| `export.py` | The CSV deliverable: one row per subreddit-month, no empty cells | aggregates | `outputs/3_FightClub_draft.csv` |
| `viz.py` | Plot style, palette, helpers (`save`, `finding_title`, `suptitle`, `caption`, `event_line`) | | `figures/` |
| `figs_overview.py` | Charts C01-C09, C03b | aggregates | `figures/` |
| `figs_text.py` | Charts C10-C18, C36 | aggregates | `figures/` |
| `figs_external.py` | Chart C33 (YouTube trending, brainrot-titled videos) | `data/external/youtube_trending_monthly.parquet` | `figures/` |
| `wordtracker.py` | **Universal word tracker**: any words or phrases (`*` = any ending, a space matches spaces and hyphens) to rate per 10,000 words and reach, per subreddit and month or year, same tokenizer and denominator as everywhere. `python -m src.wordtracker "doomscroll*" "six seven" --by year` | processed, overview_counts | prints or returns a table |
| `figs_crisis.py` | Charts C20-C24, C26-C29, C20b | daily_features, event_effects, r/nosurf rows | `figures/`, `aggregates/event_effects.parquet` |
| `figure_registry.py` | Chart-to-code-to-data map, `docs/figure_index.md`, redraw of all charts | | `docs/figure_index.md` |
| `checks.py` | Raw profile, YouTube trending profile, repeated-text and spam look-ups, spike-day analysis, emoji concentration, lexicon spot check, and the numbers quoted in notebooks 01-03 | all | `docs/numbers_checked.md` |

## Other scripts

| File | What it does |
| --- | --- |
| `run_pipeline.py` | Runs the steps above in order (`clean aggregates text features events validate csv figures checks`) |
| `tools/build_nb_01_overview.py`, `build_nb_02_text.py`, `build_nb_03_crisis.py` | Generate the three section notebooks: the text of every question (why, what, result, interpretation, next question) and the chart cells. After hand edits the notebooks are the source of truth |
| `tools/build_nb_04_external.py` | Generates `notebooks/04_external_attention.ipynb` (Q33, YouTube trending; never part of `eda.ipynb`) |
| `tools/nbhelpers.py` | Cell helpers used by the three scripts above |
| `tools/insert_h4.py` | Copies the H4 analysis (with outputs) from `notebooks/03_crisis_h4.ipynb` into Ivan's section of `eda.ipynb` and changes nothing else; safe to re-run (its cells are tagged) |
| `tools/assemble_eda.py` | Builds a DRAFT of the full story from the working notebooks into `notebooks/99_full_story_draft.ipynb` (`intermediate`: `98_intermediate_pack_draft.ipynb`). It never writes `eda.ipynb` |
| `../dataset-collection/*.py` | HW2: download (`arctic_download.py`), extraction (`extract_subreddits.py`), cleaning of the survey data (`clean_dataset.py`) |

## What is not committed
Row-level text (comments, titles) stays local: `data/processed/` (including `derived/`) and `data/reddit_arctic/` are in `.gitignore`.
The functions in `checks.py` that print comment or thread text (`repeated_texts`, `spam_candidates`, `lexicon_spot_check`, the titles in
`spike_context`) print to the terminal only. Everything a chart reads is a small aggregate in `data/aggregates/`, which is committed,
so the charts and notebooks can be re-run without the raw data.
