--------------------------------------------------------------------------------
-- TASK 2: Warm-up & Data Quality Check
-- Question: What are application and hire volumes by source, and how many 
--           applicants are missing age data?
-- Approach: Group by source to count rows and hires. Compare COUNT(*) vs COUNT(age).
-- Result: 1,500 total applicants, 118 hires. COUNT(*) is 1500 while COUNT(age) 
--         is 1488, confirming exactly 12 NULL age records.
--------------------------------------------------------------------------------
SELECT 
    source,
    COUNT(*) AS total_applicants,
    SUM(is_hired) AS total_hires
FROM applicants
GROUP BY source;

SELECT 
    COUNT(*) AS total_rows,
    COUNT(age) AS non_null_ages,
    COUNT(*) - COUNT(age) AS missing_ages
FROM applicants;


--------------------------------------------------------------------------------
-- TASK 3: Stage-Wise Conversion (Applicants Table)
-- Question: How many applicants reached each stage milestone?
-- Approach: Conditional aggregation checking non-null stage date columns.
-- Result: Applied: 1,500 -> Screened: 852 (56.8%) -> Interviewed: 456 (30.4%) 
--         -> Offered: 152 (10.1%) -> Hired: 118 (7.87%).
--------------------------------------------------------------------------------
SELECT 
    COUNT(*) AS "1. Applied",
    SUM(CASE WHEN screened_date IS NOT NULL THEN 1 ELSE 0 END) AS "2. Screened",
    SUM(CASE WHEN interviewed_date IS NOT NULL THEN 1 ELSE 0 END) AS "3. Interviewed",
    SUM(CASE WHEN offered_date IS NOT NULL THEN 1 ELSE 0 END) AS "4. Offered",
    SUM(CASE WHEN hired_date IS NOT NULL THEN 1 ELSE 0 END) AS "5. Hired"
FROM applicants;


--------------------------------------------------------------------------------
-- TASK 3 (Alternative): Stage-Wise Conversion (Funnel Events Table)
-- Question: Calculate stage counts, % of previous stage, and % of overall total.
-- Approach: CTE with stage ordering, window LAG() with explicit ORDER BY stage.
-- Result: Applied (1500, 100%), Screened (852, 56.8% prev, 56.8% total), 
--         Interviewed (456, 53.52% prev, 30.4% total), Offered (152, 33.33% prev, 10.13% total), 
--         Hired (118, 77.63% prev, 7.87% total).
--------------------------------------------------------------------------------
WITH stage_counts AS (
    SELECT 
        stage,
        COUNT(DISTINCT applicant_id) AS applicants_reached
    FROM funnel_events
    GROUP BY stage
)
SELECT 
    stage,
    applicants_reached,
    LAG(applicants_reached, 1) OVER (ORDER BY stage) AS prev_stage_applicants,
    ROUND(applicants_reached * 100.0 / LAG(applicants_reached, 1) OVER (ORDER BY stage), 2) AS pct_of_previous,
    ROUND(applicants_reached * 100.0 / (SELECT applicants_reached FROM stage_counts WHERE stage = '1. Applied'), 2) AS pct_of_total
FROM stage_counts
ORDER BY stage ASC;


--------------------------------------------------------------------------------
-- TASK 4: Source Hire Rate Ranking
-- Question: Which recruitment channels yield the highest hire rates?
-- Approach: Calculate hires / applicants using 1.0 multiplication for integer float division.
-- Result: Exact ranking: Referral 19.5% (43/221), Naukri 8.6% (22/257), 
--         LinkedIn 7.0% (18/257), Indeed 6.1% (16/262), Company Website 4.7% (13/277), 
--         Job Fair 2.7% (6/226).
--------------------------------------------------------------------------------
SELECT 
    source,
    COUNT(*) AS total_applicants,
    SUM(is_hired) AS total_hires,
    ROUND(SUM(is_hired) * 1.0 / COUNT(*), 4) AS hire_rate,
    RANK() OVER (ORDER BY SUM(is_hired) * 1.0 / COUNT(*) DESC) AS hire_rate_rank
FROM applicants
GROUP BY source
ORDER BY hire_rate DESC;


--------------------------------------------------------------------------------
-- TASK 5: Time-to-Hire Analysis (Unified Filter: hires >= 5)
-- Question: What is the average time-to-hire across Source, Department, and Recruiter?
-- Approach: Filter `is_hired = 1`, average `total_days_to_hire`, and display hire count.
-- Result: 
--   - Overall average: 35.46 days.
--   - Fastest Recruiter: Aisha Khan (28.11 days, 9 hires).
--   - Slowest Recruiter: Vikram Malhotra (41.73 days, 15 hires) — a 13.6-day spread.
--------------------------------------------------------------------------------
-- Source Breakdown
SELECT 
    source,
    COUNT(*) AS total_hires,
    ROUND(AVG(total_days_to_hire), 2) AS avg_days_to_hire
FROM applicants
WHERE is_hired = 1
GROUP BY source
HAVING COUNT(*) >= 5
ORDER BY avg_days_to_hire ASC;

-- Department Breakdown
SELECT 
    department,
    COUNT(*) AS total_hires,
    ROUND(AVG(total_days_to_hire), 2) AS avg_days_to_hire
FROM applicants
WHERE is_hired = 1
GROUP BY department
HAVING COUNT(*) >= 5
ORDER BY avg_days_to_hire ASC;

-- Recruiter Breakdown
SELECT 
    recruiter,
    COUNT(*) AS total_hires,
    ROUND(AVG(total_days_to_hire), 2) AS avg_days_to_hire
FROM applicants
WHERE is_hired = 1
GROUP BY recruiter
HAVING COUNT(*) >= 5
ORDER BY avg_days_to_hire ASC;


--------------------------------------------------------------------------------
-- TASK 6: Monthly Trends & Cohort Maturity
-- Question: How do application volume, hires, and in-process candidates trend monthly?
-- Approach: Group by `applied_month` and count total, hires, and in-process rows.
-- Result: August 2026 (126 in process) and September 2026 (163 in process) show 
--         artificially low hire rates because candidates are still actively moving through the funnel.
--------------------------------------------------------------------------------
SELECT 
    applied_month,
    COUNT(*) AS total_applicants,
    SUM(is_hired) AS hires,
    SUM(CASE WHEN final_status = 'In Process' THEN 1 ELSE 0 END) AS in_process_count,
    ROUND(SUM(is_hired) * 1.0 / COUNT(*), 4) AS raw_hire_rate
FROM applicants
GROUP BY applied_month
ORDER BY applied_month ASC;


--------------------------------------------------------------------------------
-- TASK 7: Drop-off Analysis & Recruiter Stage-by-Stage Conversion
-- Question: Where do candidate rejections occur, and how do recruiters convert candidates stage-by-stage?
-- Approach: Group rejections by `rejected_at_stage`. Aggregate stage milestones per recruiter.
-- Result: Biggest drop-off occurs at 'Applied' stage (582 candidates rejected before screening). 
--         Rejections by stage: Applied (582), Screened (339), Interviewed (265), Offered (25).
--------------------------------------------------------------------------------
-- Rejection Drop-off Analysis
SELECT 
    rejected_at_stage,
    COUNT(*) AS rejection_count
FROM applicants
WHERE final_status = 'Rejected'
GROUP BY rejected_at_stage
ORDER BY rejection_count DESC;

-- Recruiter Full Stage-by-Stage Conversion
SELECT 
    recruiter,
    COUNT(*) AS total_assigned,
    SUM(CASE WHEN screened_date IS NOT NULL THEN 1 ELSE 0 END) AS screened,
    SUM(CASE WHEN interviewed_date IS NOT NULL THEN 1 ELSE 0 END) AS interviewed,
    SUM(CASE WHEN offered_date IS NOT NULL THEN 1 ELSE 0 END) AS offered,
    SUM(is_hired) AS hired,
    ROUND(SUM(is_hired) * 1.0 / COUNT(*), 4) AS overall_hire_rate
FROM applicants
GROUP BY recruiter
ORDER BY overall_hire_rate DESC;


--------------------------------------------------------------------------------
-- PORTFOLIO VIEW: Source Performance Summary
--------------------------------------------------------------------------------
DROP VIEW IF EXISTS v_source_performance;

CREATE VIEW v_source_performance AS
SELECT 
    source,
    COUNT(*) AS total_applicants,
    SUM(is_hired) AS hires,
    ROUND(SUM(is_hired) * 1.0 / COUNT(*), 4) AS hire_rate,
    ROUND(AVG(total_days_to_hire), 2) AS avg_hire_days
FROM applicants
GROUP BY source;