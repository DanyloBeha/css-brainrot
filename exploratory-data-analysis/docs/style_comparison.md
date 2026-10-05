# Chart style: Danylo's (main) vs ours (ivan), and a standard for the H4 charts

Written 2026-10-05 for Ivan and as working notes. Scope of the restyle: **H4 charts only** (the ten charts in the H4 block of `eda.ipynb`).
Sources: `origin/main` at `10f0948` (Danylo's section of `eda.ipynb`, `fonts/`), `ivan` branch (`src/viz.py`, `src/figs_*.py`). A third branch, `origin/eda/h3`, holds a different, unmerged `eda.ipynb` (not analysed here).

## 1. What Danylo built

| Chart | Type | Data | Notes |
| --- | --- | --- | --- |
| Reddit comments / posts per day | Streamgraph (symmetric baseline) | exact monthly totals (`_monthly_totals.csv`) per subreddit | 5-month moving average, then PCHIP interpolation: very smooth |
| Share of all comments / posts | 100% stacked area | same | same smoothing |
| Comments / posts per day, six subreddits | Ridgeline, plasma gradient on a log colour scale | same | ridge height relative to each subreddit's own peak, colour = absolute activity; colour bar on the right |

All three describe **activity volume**. No statistics, intervals, tests or events on the charts; the TikTok (Aug 2018) and COVID (Mar 2020) remarks live in the text above the chart, not in it. Each chart cell is self-contained (font loader, helpers, data read, plot in one notebook cell; no `src/` module).

## 2. Style facts

| | Danylo (main) | Ours (ivan) |
| --- | --- | --- |
| Font | **Jost** (geometric sans, Futura-like), loaded from `fonts/Jost-*.ttf` with one `FontProperties(fname=...)` per weight (Light, Medium, SemiBold, Bold, ExtraBold) | matplotlib default **DejaVu Sans** |
| Title | Short topic label, **ExtraBold 34 pt, ALL CAPS**, top left ("REDDIT COMMENTS", "SHARE OF ALL COMMENTS"); ridgeline: Bold 22 pt, sentence case. No subtitle | A full **finding sentence**, bold 12-13 pt, wrapped over two lines, plus a gray 10 pt subtitle with metric and unit |
| Axis titles | Uppercase, Bold 11 pt, light gray (`#9b9b9b`): "YEAR", "COMMENTS PER DAY" (ridgeline: regular 10 pt, sentence case) | Sentence case with unit ("Comments per 10,000 words"), default weight, black; one label per row in small multiples (overlapped until 2026-10-05, now one shared label) |
| Tick labels | Light gray, 10-11 pt, no tick marks, compact numbers (75K, 2M) | black default, plain numbers |
| Grid and frame | vertical year lines only (`#e6e6e6`), **no spines**, no tick marks | horizontal light grid, top/right spines off, left/bottom spines kept |
| Legend | One **framed box top right** with a soft drop shadow, 3 x 2 grid, subreddit name above a colour bar, same order as the bands; plus **names written inside the bands** (auto white/dark text by contrast; thin bands get no label) | Mostly direct end labels or a frameless matplotlib legend at the bottom; panel titles coloured by group in small multiples; no shared legend box |
| Colour | One hue per subreddit, hand-picked, red/crimson = short-form (teenagers `#E8575F`, memes `#A82E3C`), purple = long-form (books `#C46FBC`, ELI5 `#8A2B87`), amber = baseline (`#E9A23B`), teal = nosurf (`#10A38E`). White 1 px outlines between bands. Plasma for the ridgeline | ColorBrewer Dark2 by **group**: orange = short-form, green = long-form, purple = baseline, light green = nosurf. BuGn for heatmaps, PuOr for differences, gray for context |
| Size | 13 x 8.4 in (ridgeline 11 x 7.6), margins set in inches so title and legend sit at fixed spots | 9-12 x 4.6-7 in, `tight_layout` |
| Text around the chart | 1-3 conversational sentences ("Let's take a look at...") | Fixed five-part block per question (why, what, result, interpretation, next) with numbers, plus a "Code and data" line |
| Source / caveat | none | gray caption under every chart (source, sampling, caveat) |
| Event marking | none on chart | dashed vertical lines with short labels, shaded test window |

**Palette check (validator, light mode):** Danylo's six colours pass (worst colour-blind distance dE 12.7, worst normal-vision distance 15.9). One warning: amber `#E9A23B` has 2.1:1 contrast on white, so amber must carry a direct label. Ours passes with two warnings (pink-vs-purple under protanopia, light green contrast), also covered by direct labels.

## 3. What works where

**Danylo's strengths:** one recognisable look (Jost + big caps title + soft gray axes + boxed legend), generous size, labels inside the areas, compact number format, smooth shapes. **Weaknesses:** titles name the topic, not the finding; no uncertainty or caveat on any chart; inconsistent inside his own set (caps vs sentence case, 34 vs 22 pt, legend box vs colour bar); heavy smoothing hides noise; no explanation of how to read.

**Our strengths:** finding titles, units, caveats, event lines, placebo ranges, every chart tied to code and a question. **Weaknesses:** default font, busy and small, long wrapped titles that sometimes widen the canvas, axis labels that overlapped, charts that need explaining (C20b, C23), colours that contradict his.

## 4. Conflicts the reader will see in one document

1. **Same subreddit, different colour** (his long-form is purple and nosurf teal; ours long-form is green and baseline purple). Direct contradiction between sections.
2. **Two typefaces**, two title scales, two axis-label conventions.
3. **Legend vocabulary:** boxed legend with colour bars vs end labels.
4. **Numbers:** "75K" vs "75,000"; uppercase vs sentence-case units.
5. **Level of finish:** his charts read as designed graphics, ours as analysis plots.

## 5. Proposed standard for the H4 charts

Keep our content (finding, caveat, events, placebo) and take his look, so the report reads as one piece.

1. **Font:** Jost everywhere. `fonts/` exists only on `main`, so bring it over (`git checkout origin/main -- exploratory-data-analysis/fonts`). Jost's five files all register as one family `Jost*` with weight "normal", so family-plus-weight lookup fails (that is why Danylo loads each file); register each file as its own `FontEntry` (weights 300, 500, 600, 700, 800) in `src/viz.py` so `fontweight` works in every chart.
2. **Title block (top-left, set in inches like his):** line 1 = short topic title, Jost ExtraBold, caps, about 26 pt; line 2 = the finding sentence, Jost Medium 13 pt, dark; line 3 = metric and unit, Jost Light 10 pt, gray. One helper for all ten charts.
3. **Colours:** adopt his subreddit palette as the project palette and map groups to it (short-form = crimson family, long-form = purple family, baseline = amber, nosurf = teal). H4 semantics: event lines near-black dashed, test window light gray band, placebo range light gray ribbon, real effect = group colour at full strength, non-significant = same colour at 45% opacity. Differences: a validated diverging pair from the same family (teal for fewer, crimson for more), centred on a neutral gray.
4. **Legend:** his framed top-right box for any chart with 2+ coloured series (same box, same order as the series), plus direct labels at line ends where space allows. No legend inside panels.
5. **Axes:** no spines, light vertical or horizontal grid (one orientation per chart), gray tick labels, no tick marks, compact numbers (K/M), axis titles in his small bold gray caps style with the unit, one shared axis title per figure.
6. **"How to read" line:** one sentence under the title block on every H4 chart (for example "Each panel is one event; 0 = event week; height = extra event words per 10,000 compared with the 8 weeks before"). Fixes the "I don't get it" problem on C20b, C23, C27.
7. **Size and margins:** 13 x 7.5 in base (wide, readable in the PDF), margins in inches, 200 dpi, caption (source, sampling, caveat) in 9 pt gray at the bottom, never wider than the figure.
8. **Annotations:** label the peak or the key value directly on the chart (one or two per panel), event names as small chips at the top of the dashed lines at fixed heights.

## 6. Chart-by-chart plan (H4 block)

| Chart | Today | Change |
| --- | --- | --- |
| C20 crisis words timeline | six small panels, shared y | highlight r/memes in colour, the other five gray in the same panel, events as chips, peak labelled |
| C20b event attention | four line panels, Ukraine spike dwarfs everything | a **tile matrix** (4 events x 4 communities, colour = extra event words, value written in the tile, ring = p < 0.05) as the headline, the weekly lines kept small beside it or per panel with its own y scale |
| C21 tone around events | four noisy line panels | same tile matrix for the tone change, weekly lines with the placebo ribbon behind them |
| C22 doomscroll talk | event study lines | r/nosurf line with ribbon, other five gray, bars for the four-week change |
| C23 rhythm shift | four large heatmaps | one common colour scale in the new diverging pair, hour axis in 6-hour ticks, day names, a one-line verdict per panel |
| C24 session length | four ECDF panels | one ridgeline (his style) of session length before vs after per event |
| C26 same authors | dot and interval plus band | keep, restyle, direct labels instead of text at the right |
| C27 placebo | eight histograms | forest-style strip: real effect as a big dot over the placebo dots, per community and event, sorted |
| C28 lead-lag | eight bar panels | two compact panels (tone, crisis words) with lag on x, ribbon for the noise band, one colour per group |
| C29 change-points | six small panels | keep, restyle, event chips |

## 7. Decisions (Ivan, 2026-10-05) and what was built
1. **Scope:** fonts and style apply to the H4 charts only (through `viz.h4_style()`); the other charts keep their old look.
2. **Titles:** plain topic titles inside the figure (caps, Jost ExtraBold), as Danylo does. The finding sentence and a "how to read" line are printed as ordinary text directly above the chart in the notebook (each chart cell of the H4 section of `eda.ipynb`), so they are no longer in the picture.
3. **Colours:** Danylo's palette. Long-form changed to his purple `#8A2B87` because the first group colour failed the validator against short-form. Tone tiles: first crimson = fell, teal = rose; changed later the same day to the ramp of the tone-change chart (dark blue = fell, amber = rose). Hatching means only "not beyond random dates" (C20b); in C24 outlined bars = before, solid = after.
4. **Fonts:** `fonts/` (Jost Light, Medium, SemiBold, Bold, ExtraBold, OFL licence) copied from `origin/main`; every file is registered as its own matplotlib font entry (`viz.register_jost`).
5. **Chart types** (Ivan's choices): C20 highlighted line chart (r/memes in colour, the others gray), C20b bars per event, C21 tile matrix, C22 long-run area, C23 stream graph (new), C24 grouped bars, C26 raincloud. C27, C28 and the old C23 are removed from the report; their results stay as one line each, code in `src/checks.py`.
6. **Not merged:** `main` was not merged into `ivan`; `requirements.txt` of main not touched.
7. **Later the same day:** C37 (brainrot words in event time) and C29 (tone change-points) removed from the report; C23 keeps only the stream graph; C21 uses the ramp of C26.
8. **C20 changed twice:** ridgeline first, then (Ivan) the highlighted line chart of the options board, with the peak of r/memes labelled and lines sloping to the axis where a subreddit has no usable sample.
9. **Code location:** the H4 drawing code and style helpers live only in the H4 cells of `eda.ipynb` (`src/figs_crisis.py`, the H4 block of `src/viz.py`, `notebooks/03_crisis_h4.ipynb` and the H4 build tools were removed); data preparation stays in `src/events.py`.
10. **Later still:** the other sections' charts, notebooks and the `figures/` folder were removed too (only H4 remains).
