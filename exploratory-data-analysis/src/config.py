from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "reddit_arctic"
PROC = ROOT / "data" / "processed"
AGG = ROOT / "data" / "aggregates"
EXT = ROOT / "data" / "external"
OUT = ROOT / "outputs"
for p in (PROC, AGG, EXT, OUT):
    p.mkdir(parents=True, exist_ok=True)

TEAM_ID, SEED = "FightClub", 42  # from H2_FightClub.pdf

# readme says AskReddit baseline, never downloaded
# todayilearned instead
GROUPS = {
    "short_form": ["memes", "teenagers"],
    "long_form": ["books", "explainlikeimfive"],
    "baseline": ["todayilearned"],
    "reflective": ["nosurf"],
    "news": ["worldnews", "news"],  # TODO not downloaded
    "mental": ["depression", "anxiety"],  # optional, not downloaded
}
SUB2GROUP = {s.lower(): g for g, subs in GROUPS.items() for s in subs}

# only events inside data range, dates checked 2026-10-04
EVENTS = {
    "COVID-19 pandemic declared": "2020-03-11",
    "Russia full-scale invasion of Ukraine": "2022-02-24",
    "Hamas attack / Gaza war begins": "2023-10-07",
    "Assassination of Charlie Kirk": "2025-09-10",
}

ORDER = ["memes", "teenagers", "books", "explainlikeimfive", "todayilearned", "nosurf"]
SHORT_EVENTS = {"COVID-19 pandemic declared": "COVID-19 declared", "Russia full-scale invasion of Ukraine": "Ukraine invasion",
                "Hamas attack / Gaza war begins": "Gaza war", "Assassination of Charlie Kirk": "Kirk"}
