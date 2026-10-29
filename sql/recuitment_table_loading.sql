-- Create applicants table from cleaned_funnel_data.csv
CREATE TABLE IF NOT EXISTS applicants (
    applicant_id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER,
    gender TEXT,
    experience_years REAL,
    source TEXT,
    job_role TEXT,
    department TEXT,
    recruiter TEXT,
    applied_date TEXT, -- Stored as TEXT in YYYY-MM-DD format
    screened_date TEXT,
    interviewed_date TEXT,
    offered_date TEXT,
    hired_date TEXT,
    final_status TEXT,
    rejected_at_stage TEXT,
    source_raw TEXT,
    days_applied_to_screen INTEGER,
    days_screen_to_interview INTEGER,
    days_interview_to_offer INTEGER,
    days_offer_to_hire INTEGER,
    total_days_to_hire INTEGER,
    is_hired INTEGER,
    stage_reached INTEGER,
    applied_month TEXT
);

-- Create funnel_events table from funnel_long.csv
CREATE TABLE IF NOT EXISTS funnel_events (
    applicant_id INTEGER,
    name TEXT,
    gender TEXT,
    experience_years REAL,
    source TEXT,
    department TEXT,
    job_role TEXT,
    recruiter TEXT,
    final_status TEXT,
    is_hired INTEGER,
    stage TEXT,
    stage_date TEXT, -- Stored as TEXT in YYYY-MM-DD format
    FOREIGN KEY (applicant_id) REFERENCES applicants(applicant_id)
);

select count(*) from funnel_events;
drop table applicants;
ALTER TABLE applicants ALTER COLUMN age TYPE NUMERIC;
ALTER TABLE applicants 
    ALTER COLUMN age TYPE NUMERIC,
    ALTER COLUMN days_applied_to_screen TYPE NUMERIC,
    ALTER COLUMN days_screen_to_interview TYPE NUMERIC,
    ALTER COLUMN days_interview_to_offer TYPE NUMERIC,
    ALTER COLUMN days_offer_to_hire TYPE NUMERIC,
    ALTER COLUMN total_days_to_hire TYPE NUMERIC;
