"""Facts pack for the AI #2 weekly brief.

CODE computes every number here from sql/recruitment.db. The LLM only writes
narrative around these facts. Rules:
  * aggregated numbers only: no names, no applicant rows, no gender;
  * recruiters are pseudonymous codes (REC_1 ...);
  * every fact has an ID that the brief must cite.
"""
import hashlib
import json

import pandas as pd

from src.common.db import connect_readonly

MATURE_UP_TO = "2026-06"   # cohorts applied on or before this month are treated as mature

STAGE_NAMES = ["Applied", "Screened", "Interviewed", "Offered", "Hired"]  # stage_reached 0..4


def _rate(num, den):
    return round(100.0 * num / den, 2) if den else None


def load_applicants(conn=None) -> pd.DataFrame:
    own = conn is None
    conn = conn or connect_readonly()
    df = pd.read_sql(
        "SELECT source, recruiter, final_status, is_hired, total_days_to_hire, "
        "stage_reached, rejected_at_stage, applied_month FROM applicants",
        conn,
    )
    if own:
        conn.close()
    return df


def build_facts(df: pd.DataFrame) -> dict:
    facts = []

    def add(fid, label, value, unit="", note=""):
        facts.append({"id": fid, "label": label, "value": value, "unit": unit, "note": note})

    n = len(df)
    hired = int(df.is_hired.sum())
    rejected = int((df.final_status == "Rejected").sum())
    in_process = int((df.final_status == "In Process").sum())
    avg_days = round(float(df.loc[df.is_hired == 1, "total_days_to_hire"].mean()), 2)

    add("OV_01", "Applicants in the period", n)
    add("OV_02", "Hires", hired)
    add("OV_03", "Rejected", rejected)
    add("OV_04", "Still in process", in_process, note="Not yet decided; excluded from mature rates")
    add("OV_05", "Overall hire rate", _rate(hired, n), "%")
    add("OV_06", "Average days to hire (hires only)", avg_days, "days")

    # Funnel: cumulative reach per stage, and conversion from the previous stage.
    prev = None
    for k, name in enumerate(STAGE_NAMES):
        reached = int((df.stage_reached >= k).sum())
        add(f"FN_{k + 1}", f"Reached stage: {name}", reached)
        if prev is not None:
            add(f"FN_CV_{k + 1}", f"Conversion into {name}", _rate(reached, prev), "%")
        prev = reached

    # Rejections by the stage where the candidate dropped out.
    for i, name in enumerate(STAGE_NAMES[:-1], start=1):
        add(f"REJ_{i}", f"Rejected at stage: {name}", int((df.rejected_at_stage == name).sum()))

    # Sources (six canonical sources). Source names are not personal data.
    for i, (src, g) in enumerate(sorted(df.groupby("source"), key=lambda kv: -len(kv[1])), start=1):
        h = int(g.is_hired.sum())
        note = "Few hires: treat rate as unstable" if h < 10 else ""
        add(f"SRC_{i}", f"Source: {src} - applicants", len(g))
        add(f"SRC_{i}_H", f"Source: {src} - hires", h, note=note)
        add(f"SRC_{i}_R", f"Source: {src} - hire rate", _rate(h, len(g)), "%", note=note)

    # Recruiters: pseudonymous codes, ordered by name so the mapping is stable.
    for i, (_, g) in enumerate(sorted(df.groupby("recruiter"), key=lambda kv: kv[0]), start=1):
        h = int(g.is_hired.sum())
        days = round(float(g.loc[g.is_hired == 1, "total_days_to_hire"].mean()), 2) if h else None
        note = f"Small n: only {h} hires, do not compare" if h < 10 else ""
        add(f"REC_{i}_H", f"Recruiter {i} - hires", h, note=note)
        add(f"REC_{i}_D", f"Recruiter {i} - average days to hire", days, "days", note=note)

    # Monthly cohorts with an immature flag.
    immature_months, immature_apps = [], 0
    for month, g in sorted(df.groupby("applied_month")):
        h = int(g.is_hired.sum())
        ip = int((g.final_status == "In Process").sum())
        mature = month <= MATURE_UP_TO
        note = "" if mature else "Immature cohort: outcomes still open; do not compare rates"
        if not mature:
            immature_months.append(month)
            immature_apps += len(g)
        add(f"MON_{month}", f"Cohort {month} - applicants", len(g), note=note)
        add(f"MON_{month}_R", f"Cohort {month} - hire rate", _rate(h, len(g)), "%", note=note)
        add(f"MON_{month}_IP", f"Cohort {month} - still in process", ip, note=note)

    # Caveat summary: lets the brief mention open cohorts without sending every month.
    add("CAV_01", "Cohorts after the mature cutoff (outcomes still open)", len(immature_months),
        note=("Months: " + ", ".join(immature_months)) if immature_months else "")
    add("CAV_02", "Applicants in cohorts after the mature cutoff", immature_apps,
        note="Do not compare hire rates for these cohorts")

    return {"facts": facts, "mature_cutoff": MATURE_UP_TO, "n_applicants": n}


def generate_facts_pack(conn=None) -> dict:
    pack = build_facts(load_applicants(conn))
    payload = json.dumps(pack, sort_keys=True).encode()
    pack["sha256"] = hashlib.sha256(payload).hexdigest()
    return pack


if __name__ == "__main__":
    print(json.dumps(generate_facts_pack(), indent=2)[:3000])