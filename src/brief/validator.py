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
DATE_RE = re.compile(r"\b\d{4}\s*[-\u2013/.]\s*\d{1,2}(?:\s*[-\u2013/.]\s*\d{1,2})?\b")  # 2026-07, 2026-07-01
MONTH_YEAR_RE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b20\d{2}\b")  # bare years such as 2026 are dates, not counts
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
    # Decimal form of a percent (0.0787 for 7.87%) only when written as a decimal below 1.
    # Plain integers such as 0 must match the fact itself.
    decimal_form = (not pct) and 0 < abs(value) < 1 and decimals >= 2
    candidates = [fact_value / 100.0] if decimal_form else [fact_value]
    for c in candidates:
        if round(c, decimals) == round(value, decimals) and abs(c - value) <= 0.5 * 10 ** (-decimals) + 1e-12:
            return True
    return False


def _blank(m) -> str:
    return " " * len(m.group(0))  # keep positions so we can pair numbers with citations


PROTECT_RE = re.compile(r"\[[^\]]*\]")  # citations are kept intact


def _strip_dates_and_ids(segment: str) -> str:
    # Dates first (longest patterns), then month-year, then bare years, then bare IDs.
    segment = DATE_RE.sub(_blank, segment)
    segment = MONTH_YEAR_RE.sub(_blank, segment)
    segment = YEAR_RE.sub(_blank, segment)
    return ID_RE.sub(_blank, segment)


def _clean(line: str) -> str:
    """Blank date text and bare IDs everywhere except inside [citations]. Keeps string positions."""
    out, pos = [], 0
    for m in PROTECT_RE.finditer(line):
        out.append(_strip_dates_and_ids(line[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_strip_dates_and_ids(line[pos:]))
    return "".join(out)


def validate_brief(text: str, pack: dict) -> dict:
    facts = {f["id"]: f for f in pack["facts"]}
    violations, checked, cited_all = [], 0, set()

    for line in text.splitlines():
        clean = _clean(line)
        tokens = [(m.start(), m.end(), m.lastgroup, m.group(0)) for m in TOKEN_RE.finditer(clean)]
        cites = []
        for start, end, kind, raw in tokens:
            if kind == "cite":
                cid = raw.strip("[]")
                cited_all.add(cid)
                cites.append((start, cid))
        for start, end, kind, raw in tokens:
            if kind != "num":
                continue
            checked += 1
            value, decimals, pct = _parse(raw)
            nxt = [c for c in cites if c[0] > start]
            prv = [c for c in cites if c[0] < start]
            target = (nxt[0] if nxt else (prv[-1] if prv else None))
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


# ---------------------------------------------------------------- placeholder design
PLACEHOLDER_RE = re.compile(r"\{([A-Z]{2,4}(?:_[A-Za-z0-9\-]+)+)\}")
ANY_DIGIT_RE = re.compile(r"\d")


def format_value(f: dict) -> str:
    """How a fact is shown in the brief: thousands commas for whole numbers, unit after the value."""
    v = f["value"]
    if isinstance(v, bool) or v is None:
        return "n/a"
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer() and abs(v) >= 1000):
        text = f"{int(v):,}"
    else:
        text = f"{v}"
    unit = f.get("unit") or ""
    if unit == "%":
        return text + "%"
    if unit:
        return f"{text} {unit}"
    return text


def render_brief(template: str, pack: dict) -> str:
    """Replace every {FACT_ID} with the fact's formatted value. Code writes the numbers, not the model."""
    facts = {f["id"]: f for f in pack["facts"]}
    return PLACEHOLDER_RE.sub(lambda m: format_value(facts[m.group(1)]) if m.group(1) in facts else m.group(0),
                              template)


def validate_placeholders(template: str, pack: dict) -> dict:
    """Checks the model's template before rendering.

    * every {FACT_ID} must name a fact that was sent;
    * no digit may appear anywhere outside a placeholder (code supplies every number);
    * causal wording is flagged.
    """
    facts = {f["id"]: f for f in pack["facts"]}
    violations = []
    placeholders = PLACEHOLDER_RE.findall(template)
    for fid in placeholders:
        if fid not in facts:
            violations.append({"type": "unknown_citation", "text": f"{{{fid}}}"})
        elif facts[fid].get("value") is None:
            violations.append({"type": "missing_value", "text": f"{{{fid}}}"})
    outside = PLACEHOLDER_RE.sub(" ", template)
    for m in ANY_DIGIT_RE.finditer(outside):
        start = max(0, m.start() - 12)
        violations.append({"type": "digit_outside_placeholder", "text": outside[start:m.end() + 12].strip()})
        break  # one example is enough for the retry message
    for pat in CAUSAL_PATTERNS:
        for m in re.finditer(pat, template, re.IGNORECASE):
            violations.append({"type": "causal_language", "text": m.group(0)})
    return {
        "is_valid": not violations,
        "placeholders": len(placeholders),
        "numbers_checked": len(placeholders),
        "numbers_unsupported": sum(v["type"] in ("unknown_citation", "missing_value") for v in violations),
        "citations": len(set(placeholders)),
        "violations": violations,
    }
