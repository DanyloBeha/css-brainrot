# Chart backlog

Target 30+. FT category = FT Visual Vocabulary category used to pick the chart. Kaggle appendix charts are `K01...`.

| ID | Question | Chart (FT category) | Main libs | Phase | Oct 6 | Status |
|---|---|---|---|---|---|---|
| C01 | Records per month, submissions vs comments | Stacked columns (Change over time / Part-to-whole) | DuckDB, mpl | 2 | yes | done |
| C02 | Which subreddits carry the data | Ordered horizontal bars (Ranking) | mpl | 2 | yes | done |
| C03 | Unique authors per month by subreddit | Small-multiple lines (Change over time) | DuckDB, mpl | 2 | | done (r/nosurf only, see research log) |
| C04 | How concentrated is activity among authors | ECDF / Lorenz, log x (Distribution) | Polars, mpl | 2 | | done (reversed Lorenz, log x) |
| C05 | Comment length by subreddit | ECDF or violin, log x (Distribution) | seaborn | 2 | yes | done |
| C06 | When do people post (UTC hour x weekday) | Heatmap, BuGn (Distribution) | seaborn | 2 | yes | done |
| C07 | Comments per submission over time | Line (Change over time) | DuckDB, mpl | 2 | | done |
| C08 | Score distribution; score vs length | ECDF + hexbin (Distribution / Correlation) | mpl | 2 | | done (score bands + share reaching 10) |
| C09 | Daily volume spikes and what caused them | Line + annotations / calendar heatmap | calplot, mpl | 2 | | done (r/nosurf) |
| C10 | Is comment length shrinking (short-form vs long-form vs baseline) | Highlight-vs-gray lines, direct labels (Change over time) | mpl | 3 | draft | done |
| C11 | Lexical diversity (MTLD) over time | Lines with CI (Change over time) | lexicalrichness | 3 | | done |
| C12 | Readability, first vs last period | Slope chart / ridgeline (Distribution / Change) | textstat, mpl | 3 | | done |
| C13 | Share of very short comments | Lines/area (Change over time) | DuckDB | 3 | | done |
| C14 | Emoji per 10k tokens | Lines (Change over time) | emoji, DuckDB | 3 | | done |
| C15 | **Brainrot terms per 10k words** by subreddit | Small multiples (Change over time) | DuckDB | 3 | draft | done |
| C16 | **Reach**: share of comments with a term | Small multiples (Change over time) | DuckDB | 3 | | done |
| C17 | Words gaining/losing (log-odds) | Diverging bars (Deviation) | numpy, mpl | 3 | | done |
| C18 | Bigrams early vs late | Bars or static network (Relationships) | sklearn, networkx | 3 | | done |
| C19 | Topic prevalence over time (stretch) | Stacked area (Part-to-whole over time) | BERTopic | 3 | | skipped (stretch) |
| C20 | Crisis-keyword talk with events marked | Line + event lines + shaded windows | mpl | 4 | draft | done |
| C21 | **Negativity around events: news vs control (spillover)** | Event-study lines + bands (Change over time) | statsmodels, mpl | 4 | | done (no news subreddits yet) |
| C22 | "doomscroll*" mentions around events | Event-study | mpl | 4 | | done |
| C23 | Activity pattern shift post minus pre | Diverging heatmap (Deviation) | seaborn | 4 | | done (r/nosurf) |
| C24 | Session length pre vs post | ECDF, log x (Distribution) | Polars, mpl | 4 | | done (r/nosurf) |
| C25 | Emotions (fear/anger/sadness) over time | Small-multiple lines | NRCLex, mpl | 4 | | skipped (no offline emotion lexicon) |
| C26 | Same users before vs after | Slope / dumbbell chart (Change) | mpl | 4 | | done (r/nosurf) |
| C27 | Is the effect real? placebo distribution | Histogram + marked real effect | numpy, mpl | 4 | | done |
| C28 | Does crisis intensity lead negativity? | Cross-correlation bars by lag (Correlation) | statsmodels | 4 | | done |
| C29 | When did the series shift? | Line + change-points + events | ruptures | 4 | | done |
| C30 | Reddit negativity vs US anxiety/depression (optional) | Indexed lines (Change over time) | pandas | 4 | | skipped (optional) |
| C31 | **News vs Brainrot (Google Trends), shape** | Two stacked panels, shared x (Change over time) | pandas, mpl | 5 | | open |
| C32 | News vs Brainrot, **size** (ratio at peak) | Annotation or single bar | mpl | 5 | | open |
| C33 | YouTube trending: lexicon share and views by publish month | Line + points with counts | pandas | 5 | | open |
| C34 | TikTok: lexicon videos and age-normalized views by month | Lines | DuckDB | 5 | | open |
| C35 | Reddit mentions vs Trends (do they co-move?) | Indexed lines (Change over time) | pandas | 5 | | open |

Extra charts added: C03b (removed and bot share), C15b (terms by year), C20b (event attention), C36 (sentiment over time), V01 (missingness, validation).
