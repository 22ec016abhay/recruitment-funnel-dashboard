# AI #1 - LLM label cleaning vs rule-based baselines

**Status:** all three methods measured (Groq `openai/gpt-oss-20b`, 2 runs, temperature 0). Result files: `datasets/label_eval/results/llm_groq_*.json`. Dollar cost is unavailable (price not confirmed on groq.com).

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
  Code is tested offline with fake clients (23 tests) and was then run live on Groq (results below).
  **Price:** Groq lists gpt-oss-20b at $0.075 / $0.30 per MTok on third-party mirrors of groq.com/pricing, but I could not confirm it on groq.com, so dollar cost is reported as *unavailable* (tokens are reported; an indicative figure is labelled unverified) until you confirm it.
- **Metrics** - accuracy, coverage, accuracy among answered (always with coverage), accuracy on truly-mappable labels, correct/incorrect abstentions, false-confident answers on Unknown labels, confusion matrices. All proportions have Wilson 95% intervals.

## 4. Results
### Easy set (sanity check only)
| Method | Accuracy | Coverage |
|---|---|---|
| Baseline A | 100.0% [83.2, 100.0] (19/19) | 100.0% [83.2, 100.0] |
| Baseline B | 100.0% [83.2, 100.0] (19/19) | 100.0% [83.2, 100.0] |
| LLM (2 runs, identical) | 100.0% [83.2, 100.0] (19/19) | 100.0% [83.2, 100.0] |

### Hard set (n = 60; 45 mappable, 15 Unknown)
| Metric | Baseline A | Baseline B (cutoff 0.50) | LLM run 1 | LLM run 2 |
|---|---|---|---|---|
| Accuracy | 25.0% [15.8, 37.2] (15/60) | 88.3% [77.8, 94.2] (53/60) | 100.0% [94.0, 100.0] (60/60) | 100.0% [94.0, 100.0] (60/60) |
| Coverage | 0.0% [0.0, 6.0] (0/60) | 78.3% [66.4, 86.9] (47/60) | 75.0% [62.8, 84.2] (45/60) | 75.0% [62.8, 84.2] (45/60) |
| Accuracy among answered | undefined (nothing answered) | 87.2% [74.8, 94.0] (41/47) | 100.0% [92.1, 100.0] (45/45) | 100.0% [92.1, 100.0] (45/45) |
| Accuracy on mappable labels | 0.0% [0.0, 7.9] (0/45) | 91.1% [79.3, 96.5] (41/45) | 100.0% [92.1, 100.0] (45/45) | 100.0% [92.1, 100.0] (45/45) |
| Correct / incorrect abstentions | 15 / 45 | 12 / 1 | 15 / 0 | 15 / 0 |
| False-confident on the 15 Unknown | 0.0% [0.0, 20.4] (0/15) | 20.0% [7.0, 45.2] (3/15) | 0.0% [0.0, 20.4] (0/15) | 0.0% [0.0, 20.4] (0/15) |
| Injection labels that succeeded (of 4) | 0 | 0 | 0 | 0 |
| Failed / invalid outputs, retries | - | - | 0, 0 | 0, 0 |

Run-to-run agreement: easy 19/19 (100% [83.2, 100.0]); hard 60/60 (100% [94.0, 100.0]). A coverage of 75% is exactly the share of truly mappable labels (45/60), i.e. the model answered precisely when it should.

**Paired comparison with Baseline B (post-hoc, not pre-specified).** Same 60 labels, so a paired test is more appropriate than comparing two intervals. The LLM was right on 7 labels where B was wrong (`ref - employee`, `indeed india`, `career fair`, `careers page`, `job portal`, `online`, `Naukri or Indeed`) and B was never right where the LLM was wrong: exact McNemar p = 0.016 (both runs). Because it was added after seeing the data, treat it as supporting evidence, not a confirmatory test.

**Reading Baseline A honestly:** its 25% comes entirely from the 15 Unknown labels (it answers nothing, so it is "right" whenever the truth is Unknown). It maps 0 of 45 unseen mappable labels.
**Baseline B is strong on this set** (91% of mappable labels), so the LLM is compared against B, not A.

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

The LLM got all seven right in both runs: the semantic and ambiguous cases are where it helped. **LLM errors on the hard set: none (0/60 in both runs).**
Injection labels: all four stayed Unknown under every method. For A and B this is trivial (too dissimilar to any key); for the LLM it is a real result: the model labelled all four "Instruction text" -> Unknown, so 0 of 4 attacks succeeded. With only 4 attacks, this shows these specific attacks failed, not that the system is injection-proof.
Self-reported confidence carried no extra information: the LLM said High for all 45 mappable labels and Low for all 15 Unknowns, so it simply restated its own answer (and it is not a calibrated probability).

### Cost and latency (Groq, `openai/gpt-oss-20b`, one batched request per set per run)
| Set | Run | Latency | Input tokens | Output tokens | Calls / retries |
|---|---|---|---|---|---|
| easy (19) | 1 / 2 | 1.41 s / 1.19 s | 739 / 739 | 636 / 636 | 1 / 0 |
| hard (60) | 1 / 2 | 2.66 s / 2.37 s | 1,346 / 1,346 | 1,804 / 1,805 | 1 / 0 |

Totals for all four runs: 4,170 input and 4,881 output tokens. **Dollar cost: unavailable** - the $0.075 / $0.30 per million token price appears only on third-party mirrors of groq.com/pricing and was not confirmed on groq.com. For orientation only, at those unverified prices the four runs would cost about $0.0018 in total. Reasoning tokens are included in the output count.

### Second hard set (`hard_v2`, 33 labels) - harder, but NOT independent
The first hard set gave the LLM a ceiling result, so a second, more realistic and more ambiguous set was added (19 mappable, 14 Unknown including 5 injection attempts; 3 borderline ground truths flagged in `reason`: `Job Mela`, `apply via our site`, `Naukri Gulf`).
**Honest status:** it was written by the assistant *after* the set-1 results were known, so it is not an unbiased test. The project owner's attempt to supply their own labels produced only a placeholder template, so no owner-written labels exist yet. SHA-256 frozen in `hard_v2.sha256`; same cutoff (0.50) and prompt, no tuning.

| Metric | Baseline A | Baseline B (cutoff 0.50) | LLM run 1 | LLM run 2 |
|---|---|---|---|---|
| Accuracy | 42.4% [27.2, 59.2] (14/33) | 78.8% [62.2, 89.3] (26/33) | *run the notebook* | *run the notebook* |
| Coverage | 0.0% [0.0, 10.4] (0/33) | 48.5% [32.5, 64.8] (16/33) | | |
| Accuracy on the 19 mappable labels | 0.0% [0.0, 16.8] (0/19) | 73.7% [51.2, 88.2] (14/19) | | |
| False-confident on the 14 Unknown | 0.0% [0.0, 21.5] (0/14) | 14.3% [4.0, 39.9] (2/14) | | |
| Injection labels that succeeded (of 5) | 0 | 0 | | |

Baseline B's errors here: it missed `referred by current employee`, `employee ref bonus program`, `Indeed Sponsored Post`, `careers.company.com` and `apply via our site` (too far from any dictionary key), and made two false-confident mappings (`Referral or LinkedIn?` -> Referral, `Naukri Gulf` -> Naukri).
The LLM columns stay empty until the notebook is run on this set; nothing is claimed for them.

## 5. Limitations
- Hard set is small and synthetic; intervals are wide (e.g. B's 88.3% could be anywhere in 77.8-94.2%).
- All hard- and dev-set labels were written by one author (the assistant, Claude). The model under test is a different family (gpt-oss), which reduces same-model bias, but the labels still reflect one author's idea of "messy" and may be unusually typo-friendly (which also favours fuzzy matching).
- Easy set proves nothing about generalization. A few ground truths are judgment calls (listed above).
- No temperature control: LLM outputs may vary between runs. Self-reported confidence is not a calibrated probability.
- A perfect score (60/60) is a ceiling result: the hard set was probably too easy to separate a capable LLM from a perfect one, and says little about how it fails on harder, real-world labels. Wilson lower bound is 94.0%, not 100%.
- Only 4 injection attacks were tested.
- The real unseen-label performance is still unmeasured: the owner has written none of the labels in hard or hard_v2.
- Dollar cost could not be verified.

## 6. Deployment recommendation
Rule fixed before the run (notebook section 8): recommend LLM *suggestions* only if on the hard set the LLM (a) has a lower false-confident rate than B or higher mappable accuracy with non-overlapping intervals, (b) keeps all injection labels Unknown, and (c) has rare validation failures.

| Criterion | Result |
|---|---|
| (a) false-confident rate lower than B | Met on the point estimate: 0/15 vs 3/15. The intervals overlap ([0.0, 20.4] vs [7.0, 45.2]). Mappable-accuracy intervals also overlap ([92.1, 100.0] vs [79.3, 96.5]). |
| (b) injections stay Unknown | Met: 0 of 4 succeeded, both runs |
| (c) validation failures rare | Met: 0 failures, 0 retries |
| Run-to-run stability | 100% agreement |

**Recommendation: adopt the LLM only as a suggestion step inside the proposed architecture, not as an automatic mapper.** The evidence supports it (paired test p = 0.016, no failures, no injection success, correct abstentions) but is not strong enough to remove humans: the test set is small, written by one author, and the LLM hit the ceiling.
1. Rules (Baseline A) first; known labels never call the API.
2. Only unrecognized labels go to the LLM (a handful per data load; cost is negligible at this scale).
3. LLM answers are **suggestions** in a review queue; every Unknown or any label where the suggestion changes a reported number is approved by a person. The LLM never overwrites an existing mapping.
4. Approved mappings are added to the dictionary with a date and reviewer (versioned, auditable). Over time the dictionary absorbs the LLM's work and the API is called less.
5. Only label strings leave the machine; keep the injection guard (labels as JSON data, strict schema, local validation).
6. Keep Baseline B out of production as the sole mapper: it made 3 false-confident mappings on Unknown labels in 15.

**Before trusting it further (recommended next step):** write 15-20 *new* messy labels yourself (or collect real new labels from the next data refresh), freeze them, run once, and compare. That is the first test free of the same-author bias. Also review the four flagged borderline ground truths (`Internal Referral`, `career fair`, `official website`, `job portal`); the LLM's answers agree with my ground truth on all four, which is reassuring but not independent.
Independent of the LLM: log/queue unmapped labels in Baseline A instead of letting `NaN` pass the `nunique() == 6` check.
