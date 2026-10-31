"""Writes docs/fairness_report.md and docs/fairness_dashboard.csv from the real database."""
from pathlib import Path

import pandas as pd

from src.fairness.fairness_check import run_fairness_audit

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def main():
    DOCS.mkdir(exist_ok=True)
    both = {"all applicants": run_fairness_audit(True), "excluding In Process": run_fairness_audit(False)}
    dash = []
    lines = ["# AI #5 - Fairness and adverse-impact check (real dataset)", "",
             "Source: `sql/recruitment.db`, read-only. Gender is used only in this analysis and never in an LLM prompt.", "",
             "**What this is:** a check of selection rates by gender in this dataset, using 95% Wilson intervals, "
             "Fisher exact tests, the 4/5ths screening ratio and stratified views.", "",
             "**What this is not:** a legal adverse-impact analysis. The 4/5ths rule is a screening heuristic. "
             "Real hiring decisions need legal and domain review.", ""]
    for name, res in both.items():
        lines += [f"## Scope: {name} (n = {res['n']})", "",
                  f"Gender counts: {res['genders']}", "",
                  "### Selection rates by stage (cumulative reach, 95% Wilson CI)", "",
                  _md(res["stage_table"][["gender", "stage", "n", "reached", "rate_pct",
                                          "ci95_low_pct", "ci95_high_pct", "pass_from_prev_pct", "low_n"]]), "",
                  "### Adverse-impact ratio vs highest-rate group with n >= 50", "",
                  _md(res["impact"]), "",
                  "### Fisher exact test, Female vs Male, per stage", "",
                  _md(res["tests"]), ""]
        for s in res["strata"]:
            lines += [f"### Stratified by {s['by']} (Mantel-Haenszel OR for Female vs Male hire = {s['mantel_haenszel_or']})", "",
                      _md(s["strata"]) if not s["strata"].empty else "_no strata_", ""]
        for _, r in res["impact"].iterrows():
            dash.append({"scope": name, "stage": r.stage, "gender": r.gender, "n": r.n,
                         "rate_pct": r.rate_pct, "impact_ratio": r.impact_ratio,
                         "below_4_5ths": r.below_4_5ths, "low_n": r.low_n})
    lines += ["## Limits", "",
              "- Non-binary (n = 46) is below the 50-person threshold: reported, flagged, not interpreted, never a reference group.",
              "- Stratified cells are small; the Mantel-Haenszel odds ratio is a pooled summary, not a verdict.",
              "- The repository does not show how the synthetic data were generated, so this analysis cannot say what causes any gap.",
              "- The project spec states that a female disparity was planted (conversion factor 0.75). The generator notebook in this repo "
              "does not contain that factor, so this report does not treat it as established."]
    (DOCS / "fairness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.DataFrame(dash).to_csv(DOCS / "fairness_dashboard.csv", index=False)
    print("wrote docs/fairness_report.md and docs/fairness_dashboard.csv")


if __name__ == "__main__":
    main()
