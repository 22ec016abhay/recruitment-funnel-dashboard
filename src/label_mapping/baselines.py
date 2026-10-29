"""Two rule-based baselines.

Baseline A reproduces notebook/02_cleaning.ipynb exactly (strip -> lowercase -> dict .map).
It is NOT improved: unmapped labels stay NaN there, so here they are reported as 'unmapped'
and scored as Unknown (the only sensible way to score them).
"""
import difflib
import pandas as pd

CANONICAL = ["Company Website", "Indeed", "Job Fair", "LinkedIn", "Naukri", "Referral"]
UNKNOWN = "Unknown"
CLASSES = CANONICAL + [UNKNOWN]

# Copied verbatim from notebook/02_cleaning.ipynb (cell 4). Do not edit.
EXISTING_MAPPING = {
    "linkedin": "LinkedIn", "linked in": "LinkedIn",
    "referral": "Referral",
    "indeed": "Indeed",
    "company website": "Company Website", "company website ": "Company Website",
    "job fair": "Job Fair", "jobfair": "Job Fair",
    "naukri": "Naukri",
}


def normalize(label) -> str:
    return str(label).strip().lower()


def baseline_a(labels) -> pd.DataFrame:
    """Existing pandas logic. Returns predicted_source (Unknown if unmapped) and an `unmapped` flag."""
    s = pd.Series(list(labels), dtype="object")
    mapped = s.str.strip().str.lower().map(EXISTING_MAPPING)   # NaN where unmapped (original behaviour)
    return pd.DataFrame({"source_raw": s, "predicted_source": mapped.fillna(UNKNOWN), "unmapped": mapped.isna()})


# Keys as they can actually be reached after strip(): the 'company website ' key is dead code in the original.
FUZZY_KEYS = sorted({k.strip() for k in EXISTING_MAPPING})


def baseline_b(labels, cutoff: float) -> pd.DataFrame:
    """Fuzzy matching with difflib.get_close_matches against the dictionary keys.
    Below `cutoff` similarity the label is NOT mapped (Unknown)."""
    preds, matched = [], []
    for lab in labels:
        m = difflib.get_close_matches(normalize(lab), FUZZY_KEYS, n=1, cutoff=cutoff)
        preds.append(EXISTING_MAPPING[m[0]] if m else UNKNOWN)
        matched.append(m[0] if m else None)
    return pd.DataFrame({"source_raw": list(labels), "predicted_source": preds, "matched_key": matched})
