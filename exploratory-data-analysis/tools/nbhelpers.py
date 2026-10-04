import pathlib
import sys

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

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
set_style()
"""


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.figure_registry import code_ref  # noqa: E402


def md(s):
    return new_markdown_cell(s.strip("\n"))


def code(s):
    return new_code_cell(s.strip("\n"))


def q(qid, question, why, what, result, interp, nxt):
    return md(f"""### {qid}. {question}
**Why we asked:** {why}

**What we did:** {what}

**Result:** {result}

**Interpretation:** {interp}

**Next question:** {nxt}""")


def fig_cell(fn_name, module="figs_overview"):
    """The chart cell plus a line that says where its code and data come from (src/figure_registry.py)."""
    return [code(f"from src import {module} as figs\n_ = figs.{fn_name}()\nplt.show()"), md(code_ref(fn_name))]


def write(nb_cells, path):
    nb = new_notebook(cells=nb_cells)
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbformat.write(nb, path)
