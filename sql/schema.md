# Recruitment Database Schema (`recruitment.db`)

## Privacy & Security Note
*Candidate personal identifiers (such as candidate full names) have been excluded from this schema to maintain privacy compliance.*

---

## Business Definitions
- **Hire Rate:** Proportion of total applicants reaching `Hired` status ($\frac{\text{Total Hires}}{\text{Total Applicants}}$).
- **Time-to-Hire:** Calendar duration from application submission (`applied_date`) to hire date (`hired_date`). Calculated **strictly for hired applicants** (`is_hired = 1`).
- **In Process:** Active applicants who have neither been officially hired nor rejected.

---

## Allowed Categorical Values
- `final_status`: `Hired`, `Rejected`, `In Process`
- `stage` (in `funnel_events` table): `1. Applied`, `2. Screened`, `3. Interviewed`, `4. Offered`, `5. Hired`
- `rejected_at_stage`: `Applied`, `Screened`, `Interviewed`, `Offered`, `NULL` (for hired or in-process candidates)

---

## Known Data Caveats & Limitations
1. **Arbitrary Source Conflict Resolution:** Exactly 8 records contained conflicting values between original raw source tags and canonical mapping. Deduplication selected one canonical source arbitrarily based on primary key precedence rather than programmatic reconciliation rules.
2. **Missing Age Data:** 12 applicant records contain missing age values (`NULL`).
3. **Cohort Maturity Bias:** Recent months (August and September 2026) have high `In Process` volumes (126 and 163 respectively), creating artificially deflated hire rates because active candidates have not had sufficient calendar time to complete the funnel.
4. **Job Fair Efficiency Caveat:** `Job Fair` generates substantial application volume (226 applicants, comparable to other sources), but yields an extremely low hire count (6 hires, 2.7% rate).

---

## Table 1: `applicants`
One row per unique applicant (1,500 rows).

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `applicant_id` | INTEGER (PK) | Unique identifier for each applicant. |
| `age` | INTEGER | Candidate age in years (18–65). Contains 12 NULLs. |
| `gender` | TEXT | Gender category. |
| `experience_years` | REAL | Years of professional experience. |
| `source` | TEXT | Recruitment source channel. |
| `job_role` | TEXT | Target position role. |
| `department` | TEXT | Hiring department. |
| `recruiter` | TEXT | Assigned recruiter name. |
| `applied_date` | TEXT | Application submission date (`YYYY-MM-DD`). |
| `screened_date` | TEXT | Screening milestone date. |
| `interviewed_date` | TEXT | Interview milestone date. |
| `offered_date` | TEXT | Offer extension date. |
| `hired_date` | TEXT | Candidate hire date. |
| `final_status` | TEXT | Outcome (`Hired`, `Rejected`, `In Process`). |
| `rejected_at_stage` | TEXT | Drop-off point (`Applied`, `Screened`, `Interviewed`, `Offered`). |
| `days_applied_to_screen` | INTEGER | Days from application to screening. |
| `days_screen_to_interview` | INTEGER | Days from screening to interview. |
| `days_interview_to_offer` | INTEGER | Days from interview to offer. |
| `days_offer_to_hire` | INTEGER | Days from offer to hire. |
| `total_days_to_hire` | INTEGER | Total duration for hired candidates. |
| `is_hired` | INTEGER | Binary hire flag (`1` or `0`). |
| `stage_reached` | INTEGER | Maximum depth reached in funnel (1 to 5). |
| `applied_month` | TEXT | Application cohort month (`YYYY-MM`). |

---

## Table 2: `funnel_events`
Long-format event log (3,078 rows).

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `event_id` | INTEGER (PK) | Unique event identifier. |
| `applicant_id` | INTEGER (FK) | References `applicants(applicant_id)`. |
| `stage` | TEXT | Funnel stage milestone (`1. Applied`, `2. Screened`, `3. Interviewed`, `4. Offered`, `5. Hired`). |
| `stage_date` | TEXT | Event date (`YYYY-MM-DD`). |

---

## View: `v_source_performance`
Summary table aggregating metrics by recruitment channel.

