# Label evaluation sets (AI #1)

Only source-label strings are stored here. No applicant data.

| File | Rows | Author | Use |
|---|---|---|---|
| easy.csv | 19 | project dataset | Sanity check |
| dev.csv | 30 | assistant | Choose the fuzzy cutoff ONLY |
| hard.csv | 60 | assistant (0 labels from the project owner so far) | Final test; frozen after approval |
| hard_v2.csv | 33 | assistant (written after hard.csv results were known; NOT independent) | Second, harder test; frozen (hard_v2.sha256) |

## Easy set - read this first
The existing dictionary was built from these 19 labels, so Baseline A is expected to score 100% by construction.
This set is a sanity check, not evidence of generalization. Ground truth = the "Source Mapping" tab in
excel_audit/project_documentation.xlsx (verified identical to the dictionary in 02_cleaning.ipynb).

## Dev set
Disjoint from easy and hard (checked on strip+lowercase form). Never use the hard set to tune anything.

## Hard set
45 mappable labels + 15 Unknown (11 ambiguous/missing/out-of-set, 4 prompt-injection attempts).
Authorship: every label was written by the assistant (Claude). The `author` column lets the project owner add
labels tagged `user`. Limitation: labels written by the same model family that is being evaluated may share its
blind spots and idea of "typical" messy labels, which can inflate LLM accuracy.
Borderline ground truth flagged for owner review: `Internal Referral`, `career fair`, `official website`, `job portal`.
Injection labels are passed only as JSON data, never concatenated into instructions.

## Freeze rule
After the owner approves, hard.csv is frozen (its SHA-256 is recorded in the report). Any later label change must be
appended to hard_set_changelog.csv with the reason.

Regenerate with `python datasets/label_eval/build_label_sets.py`.
