"""Assemble a DRAFT of the full story (and the intermediate pack) from the executed section notebooks into notebooks/.
It does not touch eda.ipynb: that is the team notebook, and only Ivan's H4 section may be filled (tools/insert_h4.py)."""
import re, sys
import nbformat
from nbformat.v4 import new_markdown_cell, new_code_cell, new_notebook

import pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[1])
SUBSET = len(sys.argv) > 1 and sys.argv[1] == "intermediate"
KEEP_FIGS = {"c01", "c02", "c05", "c06", "c10", "c15", "c20"}      # intermediate pack (plus data prep and the question log)

def load(name):
    return nbformat.read(f"{ROOT}/notebooks/{name}.ipynb", 4).cells

def split(cells):
    """-> list of blocks: (qid, [cells]); the cells before the first question get qid None."""
    blocks, cur = [], (None, [])
    for c in cells[2:]:                                    # skip title and setup
        m = re.match(r"### (Q\w+)\.", c.source) if c.cell_type == "markdown" else None
        if m:
            blocks.append(cur); cur = (m.group(1), [c])
        else:
            cur[1].append(c)
    blocks.append(cur)
    return [b for b in blocks if b[1]]

b1, b2, b3 = split(load("01_overview_activity")), split(load("02_text_h1")), split(load("03_crisis_h4"))
byq = {q: cells for blocks in (b1, b2, b3) for q, cells in blocks if q}
prep = [c for q, cells in b1 if q is None for c in cells]
intro2 = [c for q, cells in b2 if q is None for c in cells]
intro3 = [c for q, cells in b3 if q is None for c in cells]

def fig_of(cells):
    for c in cells:
        if c.cell_type == "code":
            m = re.search(r"figs\.(c\w+)\(", c.source)
            if m: return m.group(1)

def want(q):
    if not SUBSET: return True
    return fig_of(byq[q]) in KEEP_FIGS

ANSWERS = {
 "Q1": "Peak of 6.6M records a month in July 2020, down to 1.4M by September 2026.",
 "Q2": "r/teenagers and r/memes hold 71% of all records; our sample covers 1.4-1.5% of them, but 100% of r/nosurf.",
 "Q3": "r/nosurf grew from about 21 commenters a month (2012-15) to about 2,400 (2025).",
 "Q3b": "Removed or deleted comments fell from 8% to 4%; bots reach 13% of r/nosurf comments.",
 "Q4": "The top 1% of r/nosurf authors write 24% of its messages.",
 "Q5": "Median comment: 6 words in r/teenagers, 7 in r/memes, 32 in r/explainlikeimfive.",
 "Q6": "Writing peaks around 16:00 UTC; a weekend day is about 8% quieter.",
 "Q7": "Comments per post rose in r/memes (1.3 to 20, 2015-2025) and fell in r/books (13 to 10).",
 "Q8": "45-60% of comments end at a score of 1 or less; long comments reach 10 points more often.",
 "Q9": "Busiest day 11 Sep 2025 (530 comments), driven by threads about the killing of Charlie Kirk.",
 "Q10": "Short-form comments shrank until 2019 (r/memes) or 2022 (r/teenagers), then recovered; long-form is flat.",
 "Q11": "Comments of 5 words or fewer peaked near 50% in the short-form communities; now 24-41%.",
 "Q12": "No: MTLD rose in every community (r/teenagers 118 to 148).",
 "Q13": "No: reading ease moved by at most 6 points, toward harder.",
 "Q14": "Emoji peaked at 399 per 10,000 words in r/teenagers (2018); the long-form communities stay at or below 14.",
 "Q15": "Brainrot terms: near zero before 2022, peaks of 5-7 per 10,000 words in short-form, mostly faded by 2026.",
 "Q15b": "Slang (rizz, skibidi) came and went; 'brain rot' itself is 83% of hits in 2026.",
 "Q16": "At most about 1 in 100 comments contains a term.",
 "Q17": "Short-form talk moved from school and college words to bro, women, men.",
 "Q18": "The most frequent word pairs did not change.",
 "Q36": "Tone fell in four of six communities over many years (r/nosurf 0.36 to 0.16).",
 "Q20": "Only r/memes has a clear crisis-word peak (March 2022, 4.1 times its median).",
 "Q20b": "Event words rose in 13 of 16 community-event pairs; r/todayilearned barely reacted.",
 "Q21": "Tone was lower after 11 of 12 violent-event pairs, by at most 0.05 compound points.",
 "Q22": "No clear rise in doomscroll talk (Ukraine +0.8 per 10,000 words, p = 0.05).",
 "Q23": "r/nosurf's daily rhythm did not shift beyond what random dates produce.",
 "Q24": "r/nosurf session length unchanged (median 6-9 minutes).",
 "Q26": "The same authors wrote 0.04-0.07 less positively; only Kirk lies beyond random dates.",
 "Q27": "3 of 16 tests outside the random range (0.8 expected): too weak to call a finding.",
 "Q28": "No relation with world uncertainty (largest |r| 0.19, noise band 0.15).",
 "Q29": "1 of 17 change-points lies near an event (about 3 expected by chance).",
}


def qrow(q):
    title = re.match(r"### Q\w+\. (.*)", byq[q][0].source).group(1)
    return f"| {q} | {title} | answered | {ANSWERS[q]} |"


ORDER_Q = ["Q1", "Q2", "Q3", "Q3b", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "Q15b", "Q16",
           "Q17", "Q18", "Q36", "Q20", "Q20b", "Q21", "Q22", "Q23", "Q24", "Q26", "Q27", "Q28", "Q29"]
shown = [q for q in ORDER_Q if want(q)]

HEADER = """# Exploratory Data Analysis

## Time spent
|  Name  | Time   |
| ---    |  ---   |
| Danylo | 40 min |
| Ivan   | 5 min  |
| Daryna | 0 min  |

## Plan (temporary)
- Danylo: reddit and H1
- Ivan and Daryna: kaggle

## Overview
We use the assignment's guidelines as a baseline and go further by following our own questions. H1-H4 are starting points; we look for evidence for and against them and add new questions when the data surprises us.

The graded core is the **Reddit** data: six subreddits, January 2012 to September 2026, from the Arctic Shift archive. The Kaggle survey datasets (H3) are a separate appendix at the end. The notebook follows the order **Overview, Activity and distributions, Content analysis, Interesting findings**; H1-H4 appear as threads inside it.

### Hypotheses
- H1: Discourse is getting shorter and simpler
    - Lexical & NLP approach
    - Temporal/Behavioral aspect
- H2: Short-form platforms accelerated the degradation of discourse
- H3: Wellbeing is getting worse among doomscrollers
- H4: Crises intensify doomscrolling and negativity

### Additional approches
- questionnaire
- YouTube comments"""

SURPRISES = """## Surprise log
| Date | What we saw | Follow-up |
| --- | --- | --- |
| 2026-10-04 | The raw Reddit files are a deterministic time-slot sample (about 10k comments and 2k posts per subreddit-month), not the full data | Exact monthly totals for volumes; the sample only for rates, shares and text metrics (Q2) |
| 2026-10-04 | The baseline subreddit named in the README, r/AskReddit, is not in the data; r/todayilearned is | r/todayilearned is the baseline; decide whether to download r/AskReddit |
| 2026-10-04 | No news or mental-health subreddits on disk | H4 is run on non-news communities only; r/worldnews and r/news need to be downloaded for the contrast group |
| 2026-10-04 | r/memes comments rose from 0.23M in 2017 to 34.5M in 2020 and then fell by 92% to 2.8M in 2025; all six subreddits together peaked at 6.6M records in July 2020 and are at 1.4M | Find out what happened in the subreddit; a decline this large matters for every trend (Q1) |
| 2026-10-04 | Comment length did not shrink steadily: r/teenagers fell until 2022 and r/memes until 2019, then both recovered | H1 is not supported as a general trend; separate composition from behaviour (Q10) |
| 2026-10-04 | Moderator messages, link bots and one spam burst (177 comments of about 1,800 words each in r/teenagers, 2026) were among the most frequent texts | Added cleaning rules; tokenizer now straightens curly apostrophes (Q5, Q15, and the data section) |
| 2026-10-04 | The busiest r/nosurf day (11 Sep 2025) is driven by threads about the killing of Charlie Kirk, seen by some users on short-video feeds | Added the event to the H4 list after verifying its date (Q9, Q20b) |
| 2026-10-04 | An early r/nosurf spike (12 Feb 2021, 355 comments in 115 threads) vanished after removing moderator and templated messages | It was removal notices posted across many threads; the cleaning rules matter for daily series (Q9, data section) |
| 2026-10-04 | Positive tone fell in four of six communities over many years, long before any event (r/nosurf 0.36 to 0.16) | Baseline drift is larger than any event effect found (Q36, Q29) |
| 2026-10-04 | Event words rose in every conversational community after every event, but tone barely moved | The events reach the communities; the effect on tone is small (Q20b, Q21, Q27) |"""

TEMPLATE = """## Template for every analysis
```markdown
### Q7. <the question>
**Why we asked:** what made us think of it (earlier plot, hypothesis, surprise)
**What we did:** data used, filters, metric, and why this chart type
**Result:** what the chart shows, with numbers
**Interpretation:** our explanation, plus caveats
**Next question:** what this made us curious about
```"""

SETUP = """import sys, pathlib
ROOT = pathlib.Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
%load_ext autoreload
%autoreload 2
import warnings; warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import pandas as pd
from src.viz import set_style, GROUP_COLORS, SUB_COLORS, ACCENT, GRAY, save, finding_title, caption, event_line, highlight_vs_gray
from src.config import AGG, EXT, EVENTS, GROUPS
set_style()"""

cells = [new_markdown_cell(HEADER)]
qlog = "## Question log\n| ID | Question | Status | Answer (one line) |\n| --- | --- | --- | --- |\n" + "\n".join(qrow(q) for q in shown)
if SUBSET:
    qlog += "\n\nThe full question log is longer; this intermediate pack shows a first selection. Planned and not yet done: external attention signals (Google Trends, YouTube trending, TikTok), news subreddits for H4, Kaggle survey appendix (H3)."
else:
    qlog += "\n| Q30-Q35 | External attention (Google Trends, YouTube, TikTok, triangulation) | open | needs data files from the team |\n| K01... | Kaggle survey appendix (H3) | open | separate appendix |"
cells += [new_markdown_cell(qlog), new_markdown_cell(SURPRISES), new_markdown_cell(TEMPLATE), new_code_cell(SETUP)]

def add(q):
    if q in shown: cells.extend(byq[q])

cells.append(new_markdown_cell("# 1. Overview of the data"))
cells.extend(prep)
for q in ("Q1", "Q2"): add(q)
cells.append(new_markdown_cell("# 2. Activity and distributions"))
for q in ("Q3", "Q3b", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9"): add(q)
cells.append(new_markdown_cell("# 3. Content analysis (H1 and H2 threads)"))
cells.extend(intro2)
for q in ("Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "Q15b", "Q16", "Q17", "Q18", "Q36"): add(q)
if not SUBSET or any(q in shown for q in ("Q20", "Q20b")):
    cells.append(new_markdown_cell("# 4. Interesting findings: crises and doomscrolling (H4)"))
    cells.extend(intro3)
    for q in ("Q20", "Q20b", "Q21", "Q22", "Q23", "Q24", "Q26", "Q27", "Q28", "Q29"): add(q)
if not SUBSET:
    cells.append(new_markdown_cell("""# 5. Beyond Reddit (pending data)
Planned and not done yet: Google Trends (news versus brainrot, shape and size), YouTube trending videos by publish month, TikTok videos by month with age-normalized views, and a triangulation of Reddit mentions with Trends. They need data files that must be downloaded by hand or with credentials (Trends CSV export, Kaggle token, Hugging Face token with the dataset conditions accepted). The caveats are written in `docs/research_log.md`."""))
    cells.append(new_markdown_cell("""# 6. Where we stand on H1-H4
- **H1 (shorter and simpler): not supported as a general trend.** Comments in the short-form communities got shorter until 2019 (r/memes) or 2022 (r/teenagers) and have since become longer again; long-form communities are flat. Vocabulary variety (MTLD) rose, reading ease fell by at most 6 points, very short comments peaked and receded (Q10-Q13). Composition effects (who writes) are not separated from behaviour.
- **H2 (short-form platforms accelerated it): not testable with Reddit alone.** The brainrot vocabulary appeared in 2022-23 in the short-form communities and faded within about two years, while the umbrella term stays in use (Q15-Q17). Whether platforms caused this needs the external signals (section 5).
- **H3 (wellbeing and doomscrolling): see the Kaggle appendix.** Not part of the Reddit analysis.
- **H4 (crises): events reach the communities, effects on tone are small and mostly within random variation.** Tone dipped after the three violent events in 11 of 12 community-event pairs, three of 16 tests are outside the placebo range, doomscrolling proxies and the daily rhythm did not change, and no relation with a monthly uncertainty index (Q20b-Q29). The news-subreddit contrast is missing.

**Limitations.** The Reddit data are a time-slot sample (Q2); volumes use exact totals, rates come from the sample. VADER is not yet validated against hand labels. Everything is community-level association; nothing here says anything about individual people or their wellbeing."""))
    cells.append(new_markdown_cell("""# Appendix: Kaggle surveys (H3)
> Placeholder kept from the first draft: "Danylo - reddit and H1; Ivan & Daryna - kaggle". The survey datasets (social media addiction, doomscrolling, reels and attention) are analyzed separately from the Reddit core. Charts here are numbered K01, K02, ..."""))

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = f"{ROOT}/notebooks/98_intermediate_pack_draft.ipynb" if SUBSET else f"{ROOT}/notebooks/99_full_story_draft.ipynb"      # never eda.ipynb: that file is the team's
nbformat.write(nb, out)
print("wrote", out, len(cells), "cells")
