"""AI #5: gender selection rates, adverse-impact ratios and small-sample checks.

Runs on the real dataset (sql/recruitment.db) through a read-only connection.
Gender is used ONLY here, never in any LLM prompt.

What this module can and cannot say:
  * it measures the synthetic dataset as it is; it is not evidence about real hiring;
  * the 4/5ths ratio is a screening heuristic, not a legal test;
  * groups under SMALL_N are reported but flagged and never used as a reference group.
"""
import math

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from src.common.db import connect_readonly

SMALL_N = 50
FOUR_FIFTHS = 0.80
STAGES = {"Screened": 1, "Interviewed": 2, "Offered": 3, "Hired": 4}  # reached if stage_reached >= value
Z = 1.96


def wilson(k: int, n: int):
    """Wilson score 95% interval for a proportion, returned as (low, high) in 0..1."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denom
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def load(conn=None) -> pd.DataFrame:
    own = conn is None
    conn = conn or connect_readonly()
    df = pd.read_sql(
        "SELECT gender, source, department, experience_years, final_status, is_hired, "
        "stage_reached FROM applicants",
        conn,
    )
    if own:
        conn.close()
    df["exp_band"] = pd.cut(df.experience_years, [-np.inf, 3, 7, np.inf],
                            labels=["<3 yrs", "3-7 yrs", "7+ yrs"])
    return df


def stage_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per gender and stage: reached count, rate with Wilson CI, and conditional pass rate."""
    rows = []
    for g, gdf in df.groupby("gender"):
        n = len(gdf)
        prev = n
        for stage, k in STAGES.items():
            reached = int((gdf.stage_reached >= k).sum())
            lo, hi = wilson(reached, n)
            rows.append({
                "gender": g, "stage": stage, "n": n, "reached": reached,
                "rate_pct": round(100 * reached / n, 2) if n else None,
                "ci95_low_pct": round(100 * lo, 2), "ci95_high_pct": round(100 * hi, 2),
                "pass_from_prev_pct": round(100 * reached / prev, 2) if prev else None,
                "low_n": n < SMALL_N,
            })
            prev = reached
    return pd.DataFrame(rows)


def adverse_impact(table: pd.DataFrame) -> pd.DataFrame:
    """Ratio of each group's rate to the highest rate among groups with n >= SMALL_N, per stage."""
    out = []
    for stage, sdf in table.groupby("stage", sort=False):
        eligible = sdf[~sdf.low_n]
        if eligible.empty:
            continue
        ref = eligible.loc[eligible.rate_pct.idxmax()]
        for _, r in sdf.iterrows():
            ratio = round(r.rate_pct / ref.rate_pct, 3) if ref.rate_pct else None
            out.append({
                "stage": stage, "gender": r.gender, "n": r.n, "rate_pct": r.rate_pct,
                "reference_group": ref.gender, "reference_rate_pct": ref.rate_pct,
                "impact_ratio": ratio,
                "below_4_5ths": bool(ratio is not None and ratio < FOUR_FIFTHS and not r.low_n),
                "low_n": bool(r.low_n),
            })
    return pd.DataFrame(out)


def pairwise_tests(df: pd.DataFrame, a: str = "Female", b: str = "Male") -> pd.DataFrame:
    """Fisher exact test (two-sided) comparing two genders at each stage."""
    rows = []
    sub = df[df.gender.isin([a, b])]
    for stage, k in STAGES.items():
        ga, gb = sub[sub.gender == a], sub[sub.gender == b]
        xa, xb = int((ga.stage_reached >= k).sum()), int((gb.stage_reached >= k).sum())
        table = [[xa, len(ga) - xa], [xb, len(gb) - xb]]
        _, p = fisher_exact(table)
        rows.append({"comparison": f"{a} vs {b}", "stage": stage,
                     f"{a}_reached": xa, f"{a}_n": len(ga), f"{b}_reached": xb, f"{b}_n": len(gb),
                     "p_value_two_sided": round(float(p), 4)})
    return pd.DataFrame(rows)


def stratified_hire(df: pd.DataFrame, by: str, a: str = "Female", b: str = "Male") -> dict:
    """Hire rate by gender within each stratum, plus a Mantel-Haenszel odds ratio across strata."""
    strata, num, den = [], 0.0, 0.0
    for key, sdf in df.groupby(by, observed=True):
        fa, fb = sdf[sdf.gender == a], sdf[sdf.gender == b]
        na, nb = len(fa), len(fb)
        if na == 0 or nb == 0:
            continue
        ha, hb = int(fa.is_hired.sum()), int(fb.is_hired.sum())
        n = na + nb
        num += ha * (nb - hb) / n
        den += hb * (na - ha) / n
        strata.append({by: str(key), f"{a}_n": na, f"{a}_hired": ha, f"{b}_n": nb, f"{b}_hired": hb,
                       f"{a}_rate_pct": round(100 * ha / na, 2), f"{b}_rate_pct": round(100 * hb / nb, 2),
                    "low_n": min(na, nb) < 30 or min(ha, hb) < 10})
    mh = round(num / den, 3) if den else None
    return {"by": by, "strata": pd.DataFrame(strata), "mantel_haenszel_or": mh}


def run_fairness_audit(include_in_process: bool = True) -> dict:
    df = load()
    if not include_in_process:
        df = df[df.final_status != "In Process"]
    table = stage_table(df)
    return {
        "scope": "all applicants" if include_in_process else "excluding In Process",
        "n": int(len(df)),
        "genders": df.gender.value_counts().to_dict(),
        "stage_table": table,
        "impact": adverse_impact(table),
        "tests": pairwise_tests(df),
        "strata": [stratified_hire(df, "source"), stratified_hire(df, "department"),
                   stratified_hire(df, "exp_band")],
    }


if __name__ == "__main__":
    res = run_fairness_audit()
    pd.set_option("display.width", 200)
    print(res["scope"], res["n"], res["genders"])
    print(res["stage_table"].to_string(index=False))
    print(res["impact"].to_string(index=False))
    print(res["tests"].to_string(index=False))
