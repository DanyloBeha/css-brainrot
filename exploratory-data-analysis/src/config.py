"""Paths, subreddit groups, events and seed for the HW3 EDA."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # exploratory-data-analysis/
RAW = ROOT / "data" / "reddit_arctic"
PROC = ROOT / "data" / "processed"
AGG = ROOT / "data" / "aggregates"
EXT = ROOT / "data" / "external"
OUT = ROOT / "outputs"
for p in (PROC, AGG, EXT, OUT):
    p.mkdir(parents=True, exist_ok=True)

TEAM_ID, SEED = "FightClub", 42                        # team id taken from H2_FightClub.pdf

# Groups follow the README (H1) and what is really on disk.
# The README names r/AskReddit as baseline, but it was never downloaded:
# r/todayilearned is the baseline in the data we have.
GROUPS = {
    "short_form": ["memes", "teenagers"],
    "long_form": ["books", "explainlikeimfive"],
    "baseline": ["todayilearned"],
    "reflective": ["nosurf"],
    "news": ["worldnews", "news"],                     # not downloaded yet (H4)
    "mental": ["depression", "anxiety"],               # optional, not downloaded yet
}
SUB2GROUP = {s.lower(): g for g, subs in GROUPS.items() for s in subs}

# Only events inside the data range (2012-01 .. 2026-09). All four dates were checked against news and reference
# sources on 2026-10-04 (WHO declaration; start of the full-scale invasion; Hamas attack; Utah Valley University shooting).
EVENTS = {
    "COVID-19 pandemic declared": "2020-03-11",
    "Russia full-scale invasion of Ukraine": "2022-02-24",
    "Hamas attack / Gaza war begins": "2023-10-07",
    "Assassination of Charlie Kirk": "2025-09-10",
}

ORDER = ["memes", "teenagers", "books", "explainlikeimfive", "todayilearned", "nosurf"]          # row order of the charts
SHORT_EVENTS = {"COVID-19 pandemic declared": "COVID-19 declared", "Russia full-scale invasion of Ukraine": "Ukraine invasion",
                "Hamas attack / Gaza war begins": "Gaza war", "Assassination of Charlie Kirk": "Kirk"}   # event names on the charts
