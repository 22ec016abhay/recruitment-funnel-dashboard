"""Metrics with Wilson 95% confidence intervals.

Definitions (n = all examples in the set; failed LLM predictions are counted as abstentions=Unknown):
  accuracy            = correct / n                      (an Unknown answer is correct when truth is Unknown)
  coverage            = answered / n                     (answered = prediction is not Unknown)
  accuracy_answered   = correct among answered / answered (NEVER report without coverage)
  accuracy_known      = correct among truth!=Unknown / n_known
  correct_abstention  = truth Unknown & predicted Unknown
  incorrect_abstention= truth known   & predicted Unknown
  false_confident     = truth Unknown & predicted a real source
"""
import math
import pandas as pd
from .baselines import CLASSES, UNKNOWN


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _fmt(k, n):
    lo, hi = wilson(k, n)
    return {"k": int(k), "n": int(n), "value": (k / n if n else float("nan")), "ci95": (lo, hi)}


def evaluate(df: pd.DataFrame, pred="predicted_source", truth="expected_source") -> dict:
    n = len(df)
    correct = df[pred] == df[truth]
    answered = df[pred] != UNKNOWN
    known = df[truth] != UNKNOWN
    unk_truth = ~known
    out = {
        "total": n, "correct": int(correct.sum()), "incorrect": int((~correct).sum()),
        "accuracy": _fmt(correct.sum(), n),
        "coverage": _fmt(answered.sum(), n),
        "accuracy_answered": _fmt((correct & answered).sum(), answered.sum()),
        "accuracy_known": _fmt((correct & known).sum(), known.sum()),
        "correct_abstentions": int((unk_truth & ~answered).sum()),
        "incorrect_abstentions": int((known & ~answered).sum()),
        "false_confident": _fmt((unk_truth & answered).sum(), unk_truth.sum()),
        "n_truth_unknown": int(unk_truth.sum()),
    }
    return out


def confusion(df, pred="predicted_source", truth="expected_source") -> pd.DataFrame:
    ct = pd.crosstab(df[truth], df[pred]).reindex(index=CLASSES, columns=CLASSES, fill_value=0)
    ct.index.name = "truth \\ predicted"
    return ct


def per_class(df, pred="predicted_source", truth="expected_source") -> pd.DataFrame:
    rows = []
    for c in CLASSES:
        tp = ((df[pred] == c) & (df[truth] == c)).sum()
        fp = ((df[pred] == c) & (df[truth] != c)).sum()
        fn = ((df[pred] != c) & (df[truth] == c)).sum()
        rows.append({"class": c, "support": int((df[truth] == c).sum()), "tp": int(tp), "fp": int(fp), "fn": int(fn),
                     "precision": tp / (tp + fp) if tp + fp else float("nan"),
                     "recall": tp / (tp + fn) if tp + fn else float("nan")})
    return pd.DataFrame(rows)


def errors(df, pred="predicted_source", truth="expected_source") -> pd.DataFrame:
    return df[df[pred] != df[truth]]


def fmt(m: dict) -> str:
    """'62.5% [51.1%, 72.6%] (30/48)'"""
    lo, hi = m["ci95"]
    return f"{m['value']*100:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%] ({m['k']}/{m['n']})"


def summary_row(name: str, res: dict) -> dict:
    return {"method": name, "n": res["total"], "correct": res["correct"],
            "accuracy": fmt(res["accuracy"]), "coverage": fmt(res["coverage"]),
            "accuracy_answered": fmt(res["accuracy_answered"]),
            "false_confident_on_Unknown": fmt(res["false_confident"]),
            "correct_abstain": res["correct_abstentions"], "incorrect_abstain": res["incorrect_abstentions"]}
