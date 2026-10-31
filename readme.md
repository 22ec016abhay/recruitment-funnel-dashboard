# Recruitment Funnel & Source-of-Hire Dashboard

A people-analytics portfolio project on a **synthetic** dataset of 1,500 applicants. It covers a data pipeline
(Excel → Pandas → SQLite → Power BI), an evaluation of LLM label cleaning (AI #1), a fairness check (AI #5),
and two AI tools that read the same database: a weekly brief (AI #2) and a guarded text-to-SQL assistant (AI #3).

> **Status:** the data pipeline, AI #1, AI #5 and the dashboard are complete and tested offline (75 tests pass).
> The live LLM runs for AI #2 and AI #3 still need to be run and recorded. Their results are marked "pending" below.

---

## Dashboard

Screenshots are in `dashboard_screenshot/`.

| View | What it shows |
|---|---|
| Overview | Headline KPIs, funnel, hire rate by source, monthly cohorts |
| AI weekly brief | LLM-written brief, validated number by number against the facts |
| Fairness check | Gender selection rates by stage with 95% intervals, adverse-impact ratios |
| Ask your funnel | Plain-English questions answered with read-only SQL, SQL shown with every answer |

*(Add screenshots here once captured, for example `![Overview](dashboard_screenshot/overview.png)`.)*

---

## Key figures (from `sql/recruitment.db`)

| Measure | Value |
|---|---|
| Applicants | 1,500 |
| Hires / rejected / in process | 118 / 1,211 / 171 |
| Overall hire rate | 7.87% |
| Average days to hire (hires only) | 35.46 |
| Funnel: reached Applied, Screened, Interviewed, Offered, Hired | 1,500 → 852 → 456 → 152 → 118 |
| Hire rate: Referral / LinkedIn / Job Fair | 19.52% (41/210) / 7.03% (27/384) / 2.65% (6/226) |
| Hire rate, applicants who applied up to June 2026 | 8.84% (101/1,142) |

"Mature" means applied up to June 2026. The cutoff is a choice; later cohorts still have open outcomes.

---

## Gender selection rates (AI #5, synthetic data)

Gender counts: Male 778, Female 676, Non-binary 46.

| Hire rate | Female | Male | Impact ratio (Female vs Male) | Fisher p (hire) |
|---|---|---|---|---|
| All applicants | 5.77% (39/676) | 9.64% (75/778) | 0.60 | 0.0062 |
| Excluding In Process | 6.57% (39/594) | 10.85% (75/691) | 0.61 | 0.0077 |

- Female applicants fall below the 0.80 screening threshold at every stage. Fisher p-values are below 0.01 at all four stages.
- Pooled Mantel–Haenszel odds ratio for hire, Female vs Male: 0.59 by source, 0.57 by department, 0.58 by experience band (all applicants).
- Individual subgroups do not all point the same way. For example, Indeed and Naukri show similar or higher female hire rates, and Product and Operations show higher female rates in small cells.
- Non-binary (n = 46) is below the 50-person threshold. It is flagged, never used as a reference group, and not interpreted.

**What this cannot tell you:** why the gap exists. The repository does not show how the synthetic data were generated. The project plan says a female conversion factor of 0.75 was planted, but the generator notebook in this repository does not contain that factor, so the cause is not confirmed. This is not evidence about real hiring. A real adverse-impact review needs legal and domain expertise.

Walk-through: `notebook/04_fairness_walkthrough.ipynb`. Full tables: `docs/fairness_report.md` and `docs/fairness_dashboard.csv`.

---

## Components

| Component | What it does | Tests | Live LLM run |
|---|---|---|---|
| Data pipeline (`sql/`) | Loads cleaned data into SQLite; funnel queries | Database read-only and row counts | Not applicable |
| AI #1: label cleaning (`src/label_mapping/`) | Compares a dictionary, fuzzy matching and an LLM (Groq `openai/gpt-oss-20b`) on mapping source labels to six sources or Unknown | 23 | Done. See `docs/ai_label_cleaning.md` |
| AI #2: weekly brief (`src/brief/`) | Facts computed in code → LLM writes the brief → validator checks every number and citation → one retry → failures shown, not hidden | 15 | **Pending.** Run `python3 -m src.brief.run_brief` |
| AI #5: fairness check (`src/fairness/`) | Gender selection rates by stage, Wilson 95% intervals, Fisher tests, 4/5ths ratio, stratified views | 8 | Not applicable (no LLM) |
| AI #3: ask your funnel (`src/agent/`) | Model proposes one read-only SQL query per step (max 4); code checks every query before it runs | 15 | **Pending.** Run `python3 tests/eval_agent.py` (25 questions) |
| Retry and prompt size (`src/common/llm.py`) | Waits and retries when the provider rate-limits; smaller prompts | 9 | Not applicable |
| Dashboard (`app.py`) | Four tabs, one per component above | Headless app test: no errors | Buttons call the LLM only when pressed |

### AI #2 and AI #3 results

*(Fill in after the live runs.)*

- **AI #2 brief:** status ______; attempts ______; numbers checked ______; violations ______.
- **AI #3 evaluation (25 questions):** answerable ______ / 15; ambiguous ______ / 3 (answered without causal wording); unanswerable ______ / 3; adversarial ______ / 4 refused; average steps ______.

Until these are filled in, treat the LLM features as implemented and tested offline, but not yet measured on live data.

---

## AI #3 design

- Deterministic refusal rules run before any model call: requests for names or contact details, requests to change data, attempts to override instructions, and requests for other databases.
- The model returns one JSON action per step: `run_sql`, `answer` or `refuse`.
- SQL guard: one statement; `SELECT` or `WITH` only; no comments; no `*` selections (which would return names); no `PRAGMA`, `ATTACH`, writes or DDL; `name` columns and system tables blocked.
- Execution: read-only connection, `PRAGMA query_only`, 2-second time limit, 100-row limit.
- An answer is accepted only if every number in it appears in the last query result.
- The SQL used is returned with every answer.

## AI #2 design

- The facts pack is computed in code from the database. It has IDs for every figure, uses pseudonymous recruiter codes, and contains no gender.
- The brief is sent only the subset it may use (39 facts).
- Every number in the brief must match a fact, every citation must name a fact that was sent, and causal wording is flagged.
- One controlled retry with the violations listed. A brief that still fails is marked "not verified" and is not presented as validated.

---

## What is verified and what is not

- ✅ 75 offline tests pass: `python3 -m unittest discover tests`.
- ✅ The Streamlit app runs without errors in a headless test.
- ✅ The AI #5 walk-through notebook runs top to bottom without errors.
- ✅ All 15 answerable gold queries for AI #3 return the expected numbers.
- ⏳ Live AI #2 brief generation: pending.
- ⏳ Live AI #3 25-question evaluation: pending.
- ⏳ Screenshots: pending.

## Known issues

- `sql/schema.md` describes `stage_reached` as 1–5. The data uses 0–4 (0 = Applied, 4 = Hired). The code uses the data.
- `applicants` and `funnel_events` still contain a `name` column, although `schema.md` says names are excluded. The agent never reads it.
- `sql/queries.sql` has wrong figures in the comments for Tasks 4 and 5. Those comments need correcting.
- `v_source_performance` is not in `recruitment.db`. Any query that uses it will fail until the view is created.
- The database file is git-ignored, so a fresh clone must rebuild it with `sql/load_data.py`. That rebuild path has not yet been verified end to end.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env              # add your own GROQ_API_KEY; never commit .env
python3 tests/build_eval_set.py   # writes the 25-question evaluation set
python3 -m unittest discover tests        # offline tests, no key needed
python3 -m src.fairness.report            # AI #5 report from the real database
python3 notebook/make_fairness_notebook.py   # writes the AI #5 walk-through notebook
python3 -m src.brief.run_brief            # live AI #2 brief (needs key)
python3 tests/eval_agent.py               # live AI #3 evaluation (needs key)
streamlit run app.py                      # dashboard
```

## Repository layout


## Security and privacy

- Keys are read from `.env` (git-ignored) and are never printed, logged or written to notebooks, reports or outputs.
- Only label strings (AI #1), aggregated facts (AI #2) and user questions with schema descriptions (AI #3) are sent to the model. Applicant rows are never sent.
- Gender is used only in the AI #5 analysis, never in a prompt.
- Recruiters are pseudonymous codes in the AI #2 facts pack.

## Limitations

- All data is synthetic. Results describe the dataset, not real hiring.
- AI #1 test labels were written by an AI assistant. The project owner has not written any, so that authorship bias is not yet removed.
- Samples are small: 60 and 33 labels in AI #1, 46 Non-binary applicants in AI #5.
- Model confidence labels are self-ratings, not calibrated probabilities.
- Live LLM results are pending, so the LLM features have not been measured on real provider output.

## License

MIT. See `LICENSE`. Replace `[Your Name]` in `LICENSE` with your name before publishing.