"""Fill Ivan's H4 section of eda.ipynb with the analysis from notebooks/03_crisis_h4.ipynb, and touch nothing else.

eda.ipynb is a team notebook: only the section that starts with the markdown cell "## H4 probably" (Ivan's) may change.
Cells added by this script carry the metadata tag {"h4_block": true}, so running it again replaces them instead of
duplicating. Everything before the H4 heading and Ivan's own note cell(s) is left exactly as it is.

    python tools/insert_h4.py
"""
import pathlib
import re

import nbformat
from nbformat.v4 import new_markdown_cell

ROOT = pathlib.Path(__file__).resolve().parents[1]
EDA = ROOT / "eda.ipynb"
H4 = ROOT / "notebooks" / "03_crisis_h4.ipynb"

CONTEXT = """---
### H4 analysis: code and data
Code: `src/figs_crisis.py` (charts), `src/events.py` (event study, placebo test, change-points) and `src/textmining.py` (per-comment tone and crisis-word features). Every chart is listed in `docs/figure_index.md`, every script is explained in `docs/code_guide.md`, and the numbers quoted below are reproduced by `src/checks.py`.

**Data used here.** Six subreddits (r/memes, r/teenagers, r/books, r/explainlikeimfive, r/todayilearned, r/nosurf), January 2012 to September 2026, from Arctic Shift. The raw files are a random time-slot sample (about 10k comments per subreddit-month), except r/nosurf, which is complete. Cleaned comments only: bots, moderator messages, templated text, removed text and spam are dropped (`src/io_reddit.py`)."""

# the working notebook numbers its questions Q20-Q29 (it sits next to other working notebooks); inside eda.ipynb they are Q1-Q10
RENUMBER = {"20": "1", "20b": "2", "21": "3", "22": "4", "23": "5", "24": "6", "26": "7", "27": "8", "28": "9", "29": "10"}


def renumber(text):
    return re.sub(r"\bQ(20b|20|21|22|23|24|26|27|28|29)\b", lambda m: "Q" + RENUMBER[m.group(1)], text)


def main():
    nb = nbformat.read(EDA, 4)
    cells = [c for c in nb.cells if not c.get("metadata", {}).get("h4_block")]       # drop an earlier insertion
    assert any(c.cell_type == "markdown" and c.source.startswith("## H4") for c in cells), "Ivan's H4 heading not found"
    src = nbformat.read(H4, 4).cells[1:]                                              # skip the working notebook's title cell
    block = [new_markdown_cell(CONTEXT)] + src
    for c in block:
        c.metadata["h4_block"] = True
        if c.cell_type == "markdown":
            c.source = renumber(c.source)
    nb.cells = cells + block                                                          # the H4 section is the last one in eda.ipynb
    # sanity: nothing before Ivan's section changed
    assert all(not c.metadata.get("h4_block") for c in nb.cells[: len(cells)])
    nbformat.write(nb, EDA)
    print(f"eda.ipynb: {len(cells)} original cells kept untouched, {len(block)} H4 cells inserted after Ivan's note")


if __name__ == "__main__":
    main()
