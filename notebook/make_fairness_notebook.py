"""Writes notebook/04_fairness_walkthrough.ipynb (run once from the project root).

    python3 notebook/make_fairness_notebook.py
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip("\n")))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip("\n")))

md("""
# AI #5 - Fairness and adverse-impact check (walk-through)

**What this notebook does.** It walks through the analysis in `src/fairness/fairness_check.py` step by step,
so each number can be checked. The same code writes `docs/fairness_report.md` and `docs/fairness_dashboard.csv`.

**What it is not.** This is a screening check on a **synthetic** dataset. It describes the data; it does not show why
any gap exists, and it is not a legal adverse-impact analysis. The 4/5ths rule is a screening heuristic only.

**Rules followed.** Gender is used here only, never in an LLM prompt. The data is read from `sql/recruitment.db`
through a read-only connection. Groups under 50 people are reported but never used as the reference group.
""")

code("""
import sys
from pathlib import Path

import pandas as pd
from IPython.display import display

ROOT = Path.cwd().parent if Path.cwd().name == "notebook" else Path.cwd()
sys.path.insert(0, str(ROOT))

from src.common.db import DB_PATH, connect_readonly
from src.fairness import fairness_check as F

pd.set_option("display.width", 160)
print("Database:", DB_PATH)
""")

md("## 1. Check the data\nWe count applicants by gender before any rates are computed. Non-binary is the smallest group.")
code("""
df = F.load()
print("Applicants:", len(df))
display(df.gender.value_counts().rename("applicants").to_frame())
""")

md("""
## 2. Selection rates by stage, with 95% Wilson intervals

"Reached stage" means the candidate got at least that far (cumulative). The Wilson interval is more honest
than the simple ± formula for small groups and for rates near 0 or 100%.
""")
code("""
table = F.stage_table(df)
display(table[["gender", "stage", "n", "reached", "rate_pct", "ci95_low_pct", "ci95_high_pct", "low_n"]])
""")

md("""
## 3. Adverse-impact ratio (4/5ths screening rule)

The ratio is each group's rate divided by the highest rate among groups with at least 50 people.
A ratio below 0.80 is flagged for review. The flag is a prompt to look further, not a finding of discrimination.
""")
code("""
impact = F.adverse_impact(table)
display(impact[["stage", "gender", "n", "rate_pct", "reference_group", "impact_ratio", "below_4_5ths", "low_n"]])
""")

md("""
## 4. Are the gaps statistically clear? (Fisher exact test)

For each stage we compare Female with Male using a two-sided Fisher exact test. With a p-value below 0.05 the
difference is unlikely to be chance alone **in this dataset**. It says nothing about causes.
""")
code("""
display(F.pairwise_tests(df))
""")

md("""
## 5. Does the picture change if In Process candidates are excluded?

Candidates still in process have not had a final outcome, so excluding them gives a second view of the final outcomes.
""")
code("""
excl = F.run_fairness_audit(include_in_process=False)
print("Scope:", excl["scope"], "| n =", excl["n"], "| genders:", excl["genders"])
display(excl["impact"][excl["impact"].stage == "Hired"][["gender", "n", "rate_pct", "impact_ratio", "below_4_5ths", "low_n"]])
display(excl["tests"])
""")

md("""
## 6. Does the gap persist within groups? (stratified view)

We compare Female and Male hire rates inside each source, each department and each experience band.
The Mantel–Haenszel odds ratio pools these comparisons into one number. A value below 1 means the female hire odds are
lower overall once the grouping is accounted for. The pooled value is not the same as every subgroup: some individual
sources and departments show similar or higher female rates, so read the subgroup tables, not just the pooled number.
Small cells (for example Operations and Product) are unstable.
""")
code("""
for s in F.run_fairness_audit()["strata"]:
    print(f"\\nStratified by {s['by']} | Mantel-Haenszel OR (Female vs Male, hire) = {s['mantel_haenszel_or']}")
    display(s["strata"])
""")

md("""
## 7. Non-binary group

Non-binary has 46 applicants, below the 50-person threshold. Its rates are shown above with a `low_n` flag.
It is never used as a reference group, and the notebook does not draw conclusions from it.
""")
code("""
nb_rows = table[table.gender == "Non-binary"][["stage", "n", "reached", "rate_pct", "ci95_low_pct", "ci95_high_pct"]]
display(nb_rows)
print("Interpretation withheld: n is below 50 and the intervals are wide.")
""")

md("## 8. Export the dashboard table\nThe same table that the Streamlit Fairness tab uses.")
code("""
out_dir = ROOT / "docs"
out_dir.mkdir(exist_ok=True)
impact.assign(scope="all applicants").to_csv(out_dir / "fairness_dashboard_notebook.csv", index=False)
print("saved", out_dir / "fairness_dashboard_notebook.csv")
""")

md("""
## 9. What can and cannot be concluded

**Can be said about this synthetic dataset:**
- Female applicants reach each later stage less often than male applicants, and the differences are statistically
  clear in this dataset (sections 2–4).
- The pooled hire odds ratio stays below 1 when In Process candidates are excluded, and within source, department
  and experience band (sections 5–6). Individual subgroups do not all point the same way: for example Indeed and
  Naukri show similar or higher female hire rates, and Product and Operations show higher female rates in small cells.

**Cannot be said:**
- Why the gap exists in real life. The synthetic generator (notebook/recuitment_v2.ipynb) sets
  FEMALE_CONVERSION_FACTOR = 0.75 on purpose, so the female gap in this dataset is built in. This notebook checks that
  the method detects a planted effect. It is not evidence about real hiring.
- Anything about real hiring. Real adverse-impact analysis needs legal and domain review.
- Anything about Non-binary applicants: the group is below the threshold.
""")

nb["cells"] = C
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}
nbf.write(nb, "notebook/04_fairness_walkthrough.ipynb")
print("written notebook/04_fairness_walkthrough.ipynb")
