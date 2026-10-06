# Chart backlog

Only the H4 charts remain (decision of 2026-10-05). The charts of the other sections (C01-C18, C33, C36, V01) and C27, C28, C29 and C37 were removed from the project; their code and PNGs are in git history (commit `1850a5d` and earlier). The H4 charts are drawn by code cells in the H4 section of `eda.ipynb`; nothing is saved to `figures/` (the folder no longer exists).

| ID | Question | Chart | Status |
|---|---|---|---|
| C20 | Do crises show up in what people write? | Highlighted line chart: r/memes in colour, the other communities gray, events as chips | done (redone twice on 2026-10-05) |
| C20b | Did each event reach each community? | Bars, one panel per event; solid = beyond random dates, faded and hatched = not | done |
| C21 | Did tone get more negative after the events? (H4) | Tile matrix (4 communities x 4 events) in the colour ramp of C26, ring = beyond random dates | done (no news subreddits yet) |
| C22 | Did talk about doomscrolling rise? | Long-run area chart of r/nosurf with plasma log-colour fill, smoothed | done |
| C23 | Did brainrot words spike around the crises? | Stream graph of brainrot words in r/memes + r/teenagers | done (volume panels removed the same day) |
| C24 | Did posting sessions in r/nosurf get longer? | Grouped bars by session-length bucket, one colour per bucket, light outlined = before, solid = after | done |
| C26 | Do the same r/nosurf authors write differently? | Raincloud of per-author tone change with colour gradient | done |

Removed on 2026-10-05: C27 (placebo histograms; explained in section 4.5 of the notebook), C28 (lead-lag with the uncertainty index; null result in one line), C29 (tone change-points; one line in the summary), C37 (brainrot words in event time; covered by C23), the first C23 (rhythm heatmaps; null result in one line).
