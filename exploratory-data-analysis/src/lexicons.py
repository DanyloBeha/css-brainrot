"""Lexicons and the one tokenizer used for numerator and denominator.

All strings are written for DuckDB SQL (single quotes already escaped, RE2 syntax).
"""
CORE = ["brain[ -]?rot\\w*", "skibidi"]
EXTENDED = ["rizz(?:ler|ed|ing|es|y)?", "gyatt", "fanum tax", "mewing", "tralalero", "tung tung"]
AMBIGUOUS = ["sigma"]                       # report as a separate tier
DOOM = [r"doom ?scroll\w*", r"doom ?surf\w*"]

# URLs are removed before counting words or matching terms.
URL_RE = r"https?://\S+|www\.\S+"
TOKEN_RE_SQL = "[a-z0-9'']+"                 # '' = escaped quote inside a SQL string
CURLY = "’‘ʼ`"                # typographic apostrophes (mobile keyboards): "they’re" must stay one word


def build_re(terms):                        # no single quotes: safe inside SQL strings
    return r"\b(" + "|".join(terms) + r")\b"


PREFILTER = "brain|skibidi|rizz|gyatt|fanum|mewing|tralalero|tung tung|sigma|doom"   # cheap substring test before the regexes


def clean_sql(col="text"):
    """SQL expression: lower-cased text, typographic apostrophes straightened, URLs removed."""
    return f"regexp_replace(regexp_replace(lower({col}), '[{CURLY}]', '''', 'g'), '{URL_RE}', ' ', 'g')"


def n_tokens_sql(col="text"):
    return f"len(regexp_extract_all({clean_sql(col)}, '{TOKEN_RE_SQL}'))"


BRAINROT_CORE_RE = build_re(CORE)
BRAINROT_EXT_RE = build_re(EXTENDED)
BRAINROT_RE = build_re(CORE + EXTENDED)
SIGMA_RE = build_re(AMBIGUOUS)
DOOM_RE = build_re(DOOM)


# Crisis vocabulary for H4. Event-specific lists test whether an event was talked about at all (manipulation check);
# CRISIS_GENERAL is the broad "crisis talk" list used for the timeline.
EVENT_TERMS = {
    "covid": [r"covid\w*", "coronavirus", "corona virus", "pandemic", r"lockdown\w*", r"quarantin\w*", "social distancing"],
    "ukraine": [r"ukrain\w*", r"russia\w*", "putin", "invasion", r"zelensk\w*", "kyiv", "kiev"],
    "gaza": ["gaza", "hamas", r"israel\w*", r"palestin\w*", r"hostage\w*", "netanyahu"],
    "kirk": ["kirk", "charlie kirk", "turning point", r"assassinat\w*"],
}
CRISIS_GENERAL = [r"wars?", "pandemic", r"covid\w*", "coronavirus", r"lockdown\w*", "invasion", r"ukrain\w*", "gaza", "hamas",
                  r"israel\w*", r"palestin\w*", "genocide", r"terror\w*", r"shooting\w*", r"assassinat\w*", "crisis", "recession",
                  "famine", "refugees?", "earthquake", "hurricane"]
EVENT_RE = {k: build_re(v) for k, v in EVENT_TERMS.items()}
CRISIS_RE = build_re(CRISIS_GENERAL)
CRISIS_PREFILTER = "covid|corona|pandemic|lockdown|quarantin|distancing|ukrain|russia|putin|invasion|zelensk|kyiv|kiev|gaza|hamas|israel|palestin|hostage|netanyahu|kirk|turning point|assassinat|war|genocide|terror|shooting|crisis|recession|famine|refugee|earthquake|hurricane"
