# How to rebuild everything

Raw data (`data/reddit_arctic/`, from `dataset-collection/arctic_download.py`) is never edited. Everything else is derived.

```bash
# once, from the repo root
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r exploratory-data-analysis/requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"
playwright install chromium            # only for the PDF export

cd exploratory-data-analysis
python run_pipeline.py                 # clean -> aggregates -> text -> features -> events -> csv (about 8 min)
# the H4 section of eda.ipynb (text and chart code) is edited in eda.ipynb itself; run its cells to draw the H4 charts
jupyter nbconvert --to notebook --execute eda.ipynb --output-dir /tmp --output eda_run.ipynb      # optional: run it all without touching eda.ipynb
```

| Folder | What is in it | In git |
| --- | --- | --- |
| `src/` | all logic: `io_reddit` (cleaning), `aggregates`, `textmining`, `events` (H4 statistics), `sessions`, `export` | yes |
| `data/processed/` | row-level cleaned Parquet (`*.parquet`) and `derived/` (lexicon matches, per-comment features, a VADER label sample): contains comment text | **no** |
| `data/aggregates/` | small tables every chart reads from | yes |
| `data/external/` | World Uncertainty Index (monthly), Trends / YouTube / TikTok extracts when they exist; `raw/` holds downloads | extracts yes, `raw/` no |
| `outputs/` | PDFs and the CSV | `3_FightClub.csv` only (see `.gitignore`) |
