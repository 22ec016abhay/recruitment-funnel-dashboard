"""Checks a generated brief against the facts it was given.

Each number must match the fact cited next to it (the next citation on the same line,
or the previous one if none follows). Numbers with no citation are violations.
Citations must name a fact that was sent. Causal wording is flagged.
"""
import re

NUM = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|-?\d+(?:\.\d+)?%?"
CITE = r"\[[A-Z]{2,4}(?:_[A-Za-z0-9\-]+)+\]"
TOKEN_RE = re.compile(rf"(?P<cite>{CITE})|(?P<num>(?<![A-Za-z_\d])(?:{NUM})(?![A-Za-z_\d]))")
ID_RE = re.compile(r"(?<!\[)\b[A-Z]{2,4}(?:_[A-Za-z0-9\-]+)+\b(?!\])")
DATE_RE = re.compile(r"\b\d{4}-\d{2}\b")
CAUSAL_PATTERNS = [
    r"\bbecause\b", r"\bcaused?\b", r"\bdue to\b", r"\bdriven by\b", r"\bleads? to\b",
    r"\bresult(?:s|ed)? (?:in|from)\b", r"\bexplains?\b", r"\bthe reason\b",
]


def _parse(tok: str):
    pct = tok.endswith("%")
    raw = tok.rstrip("%").replace(",", "")
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    return float(raw), decimals, pct


def _matches(value: float, decimals: int, pct: bool, fact_value: float) -> bool:
    """True if the written number equals the fact after rounding (also allows 0.0787 for 7.87%)."""
    candidates = [fact_value] if pct else [fact_value, fact_value / 100.0]
    for c in candidates:
        if round(c, decimals) == round(value, decimals) and abs(c - value) <= 0.5 * 10 ** (-decimals) + 1e-12:
            return True
    return False


def _blank(m) -> str:
    return " " * len(m.group(0))  # keep positions so numbers can be paired with citations


def validate_brief(text: str, pack: dict) -> dict:
    facts = {f["id"]: f for f in pack["facts"]}
    violations, checked, cited_all = [], 0, set()

    for line in text.splitlines():
        # Remove dates and bare fact IDs, keeping string positions.
        clean = DATE_RE.sub(_blank, ID_RE.sub(_blank, line))
        tokens = [(m.start(), m.lastgroup, m.group(0)) for m in TOKEN_RE.finditer(clean)]
        cites = []
        for start, kind, raw in tokens:
            if kind == "cite":
                cid = raw.strip("[]")
                cited_all.add(cid)
                cites.append((start, cid))
        for start, kind, raw in tokens:
            if kind != "num":
                continue
            checked += 1
            value, decimals, pct = _parse(raw)
            nxt = [c for c in cites if c[0] > start]
            prv = [c for c in cites if c[0] < start]
            target = nxt[0] if nxt else (prv[-1] if prv else None)
            if target is None:
                violations.append({"type": "uncited_number", "text": raw})
                continue
            fid = target[1]
            if fid not in facts:
                violations.append({"type": "unknown_citation", "text": f"[{fid}]"})
                continue
            fv = facts[fid]["value"]
            if not isinstance(fv, (int, float)) or not _matches(value, decimals, pct, float(fv)):
                violations.append({"type": "number_not_in_cited_fact", "text": raw, "cited": fid})

    for cid in sorted(cited_all - set(facts)):
        if not any(v.get("text") == f"[{cid}]" for v in violations):
            violations.append({"type": "unknown_citation", "text": f"[{cid}]"})

    for pat in CAUSAL_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            violations.append({"type": "causal_language", "text": m.group(0)})

    return {
        "is_valid": not violations,
        "numbers_checked": checked,
        "numbers_unsupported": sum(v["type"] in ("number_not_in_cited_fact", "uncited_number") for v in violations),
        "citations": len(cited_all),
        "violations": violations,
    }