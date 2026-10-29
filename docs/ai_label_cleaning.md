# AI #1 - LLM label cleaning vs rule-based baselines

**Status:** baselines measured (offline). **LLM results: NOT YET MEASURED** - they require your API key (Groq); run `notebook/03_llm_label_mapping.ipynb`, then fill section 4 from its output. Nothing below about the LLM is a result.

## 1. Objective
Decide whether an LLM should help standardize messy `source_raw` labels into six canonical sources
(Company Website, Indeed, Job Fair, LinkedIn, Naukri, Referral) or `Unknown`, compared with (A) the existing pandas dictionary and (B) `difflib` fuzzy matching.
Fair evaluation, not a demo: the LLM is judged on unseen labels *and* on abstaining when a label cannot be classified.

## 2. Data and test-set construction
| Set | n | Author | Purpose |
|---|---|---|---|
| Easy | 19 | project dataset | The real labels. **The existing dictionary was built from these labels, so Baseline A is expected to score 100% by construction; this set is a sanity check, not evidence of generalization.** Ground truth = Source Mapping tab in `excel_audit/project_documentation.xlsx` (agrees with the dictionary 19/19). |
| Dev | 30 | assistant (Claude) | Choose the fuzzy cutoff **only**. 20 mappable + 10 Unknown. |
| Hard | 60 | assistant (Claude); 0 labels from the project owner | Final test, frozen after approval (SHA-256 in `hard.sha256`; changes must be logged in `hard_set_changelog.csv`). 45 mappable + 15 Unknown, including 4 prompt-injection labels (expected: Unknown). Every row has a written reason. |

No overlap between sets (checked after strip+lowercase). Only label strings are used; no applicant data is read or sent.
Borderline ground truths flagged for owner review: `Internal Referral`, `career fair`, `official website`, `job portal`.

## 3. Methods
- **Baseline A** - existing logic unchanged (strip, lowercase, `dict.map`). Unmapped labels were `NaN` in the original; they are scored as Unknown here.
  Note: the original assertion `nunique() == 6` ignores `NaN`, so unmapped labels would pass silently.
- **Baseline B** - `difflib.get_close_matches` vs dictionary keys; below the cutoff the label stays Unknown. Cutoff **0.50**, chosen on the dev set only
  (rule fixed in advance: max dev accuracy over 0.30-0.95; ties -> higher cutoff). Dev accuracy peaks at 0.50 (28/30) and falls on both sides, so the optimum is interior, not a grid-edge artifact.
- **LLM** - provider switched by the project owner from Anthropic to **Groq, model `openai/gpt-oss-20b`** (the brief asked for the Anthropic SDK; this is a documented deviation, and the code supports both).
  Verified against Groq docs (2026-10-30): the model supports `response_format json_schema` with `strict: true`, `temperature` and `reasoning_effort` (low/medium/high). The run uses temperature 0, low reasoning effort, strict schema, one batched request.
  (Anthropic path, also verified 2026-10-29: `claude-haiku-5-5`, $0.10/$0.50 per MTok, `temperature` must be omitted, so temperature 0 is unavailable there.)
  Labels are sent as JSON data only (never inside the instructions). Output validation counts malformed JSON, missing/duplicate/unexpected ids, bad enums, extra fields, truncation and API errors; failed labels are reported as Unknown+failed, never dropped. Two runs measure variability even at temperature 0.
  Code is tested offline with fake clients (23 tests) but **has not been run against a live API yet**.
  **Price:** Groq lists gpt-oss-20b at $0.075 / $0.30 per MTok on third-party mirrors of groq.com/pricing, but I could not confirm it on groq.com, so dollar cost is reported as *unavailable* (tokens are reported; an indicative figure is labelled unverified) until you confirm it.
- **Metrics** - accuracy, coverage, accuracy among answered (always with coverage), accuracy on truly-mappable labels, correct/incorrect abstentions, false-confident answers on Unknown labels, confusion matrices. All proportions have Wilson 95% intervals.

## 4. Results
### Easy set (sanity check only)
| Method | Accuracy | Coverage |
|---|---|---|
| Baseline A | 100.0% [83.2, 100.0] (19/19) | 100.0% [83.2, 100.0] |
| Baseline B | 100.0% [83.2, 100.0] (19/19) | 100.0% [83.2, 100.0] |
| LLM | *pending* | *pending* |

### Hard set (n = 60; 45 mappable, 15 Unknown)
| Metric | Baseline A | Baseline B (cutoff 0.50) | LLM run 1 | LLM run 2 |
|---|---|---|---|---|
| Accuracy | 25.0% [15.8, 37.2] (15/60) | 88.3% [77.8, 94.2] (53/60) | pending | pending |
| Coverage | 0.0% [0.0, 6.0] (0/60) | 78.3% [66.4, 86.9] (47/60) | pending | pending |
| Accuracy among answered | undefined (nothing answered) | 87.2% [74.8, 94.0] (41/47) | pending | pending |
| Accuracy on mappable labels | 0.0% [0.0, 7.9] (0/45) | 91.1% [79.3, 96.5] (41/45) | pending | pending |
| Correct / incorrect abstentions | 15 / 45 | 12 / 1 | pending | pending |
| False-confident on the 15 Unknown | 0.0% [0.0, 20.4] (0/15) | 20.0% [7.0, 45.2] (3/15) | pending | pending |
| Injection labels that succeeded (of 4) | 0 | 0 | pending | pending |

**Reading Baseline A honestly:** its 25% comes entirely from the 15 Unknown labels (it answers nothing, so it is "right" whenever the truth is Unknown). It maps 0 of 45 unseen mappable labels.
**Baseline B is strong on this set** (91% of mappable labels). The LLM has to be compared against B, not against A.

### Error analysis - Baseline B on hard (7 errors)
| Label | Truth | Predicted | Why |
|---|---|---|---|
| `indeed india` | Indeed | LinkedIn | whole-string similarity beats the shared word "indeed" |
| `careers page` | Company Website | Referral | spurious character overlap; needs meaning, not spelling |
| `career fair` | Job Fair | Referral | same |
| `ref - employee` | Referral | Unknown | abbreviation too far from the key |
| `job portal` | Unknown | Job Fair | false-confident |
| `online` | Unknown | LinkedIn | false-confident |
| `Naukri or Indeed` | Unknown | Naukri | picks one of two named sources |

These are the cases (semantic labels, ambiguity) where an LLM could plausibly help; whether it does is untested until the notebook is run.
Injection labels: all four stayed Unknown under A and B (they are too dissimilar to any key) - this says nothing about the LLM.

### Cost and latency
Pending. Tokens, latency, retries and cost will be printed by the notebook (cost = tokens x the verified prices above; if a figure cannot be verified it must be marked unavailable).

## 5. Limitations
- Hard set is small and synthetic; intervals are wide (e.g. B's 88.3% could be anywhere in 77.8-94.2%).
- All hard- and dev-set labels were written by one author (the assistant, Claude). The model under test is a different family (gpt-oss), which reduces same-model bias, but the labels still reflect one author's idea of "messy" and may be unusually typo-friendly (which also favours fuzzy matching).
- Easy set proves nothing about generalization. A few ground truths are judgment calls (listed above).
- No temperature control: LLM outputs may vary between runs. Self-reported confidence is not a calibrated probability.
- The LLM code is untested against the live API.

## 6. Deployment recommendation
**Not yet decided - no LLM evidence.** The evaluated architecture (rules first; only unrecognized labels go to the LLM; ambiguous/low-confidence to a human queue; LLM never silently overwrites a mapping; approved corrections versioned; only label strings sent; Unknown stays Unknown) is sound regardless, because it limits blast radius.
The notebook (section 8) applies a rule fixed in advance: recommend LLM *suggestions* only if on the hard set it beats Baseline B on false-confident rate or on mappable accuracy (non-overlapping Wilson intervals), keeps all injection labels Unknown, and has rare validation failures. If it does not, keep rules + fuzzy matching (B) and send unrecognized labels to human review.
A practical note independent of the LLM: even Baseline A should log/queue unmapped labels instead of letting `NaN` pass the `nunique() == 6` check.
