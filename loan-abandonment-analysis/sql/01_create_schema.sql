-- Star schema (SQL Server / PostgreSQL compatible; minor type tweaks may apply)
CREATE TABLE dim_stage (
    stage_key INT PRIMARY KEY, stage_name VARCHAR(40) NOT NULL, stage_group VARCHAR(20) NOT NULL
);
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY, date DATE NOT NULL, year INT, quarter INT, month_num INT,
    month_name VARCHAR(3), year_month CHAR(7), week_of_year INT, day_name VARCHAR(10), is_weekend SMALLINT
);
CREATE TABLE fact_applications (
    application_id VARCHAR(15) PRIMARY KEY, customer_id VARCHAR(15),
    application_date DATE, decision_date DATE, application_date_key INT REFERENCES dim_date(date_key),
    application_month CHAR(7), application_quarter VARCHAR(8), is_partial_month SMALLINT,
    age INT, age_group VARCHAR(8), employment_type VARCHAR(20),
    monthly_income_inr DECIMAL(12,2), income_band VARCHAR(12), credit_score INT, credit_risk_band VARCHAR(15),
    loan_type VARCHAR(20), loan_amount_inr DECIMAL(14,2), loan_amount_band VARCHAR(8),
    channel VARCHAR(15), region VARCHAR(10),
    documents_submitted CHAR(3), verification_completed CHAR(3), approval_status VARCHAR(25), disbursed CHAR(3),
    processing_days DECIMAL(5,1), processing_band VARCHAR(10),
    abandonment_reason VARCHAR(30), reason_group VARCHAR(25),
    furthest_stage_order SMALLINT, furthest_stage_name VARCHAR(30),
    outcome VARCHAR(12), is_disbursed SMALLINT, is_abandoned SMALLINT, is_stalled SMALLINT,
    dropoff_stage_order SMALLINT, dropoff_stage_name VARCHAR(30)
);
CREATE TABLE fact_stage_progress (
    application_id VARCHAR(15) REFERENCES fact_applications(application_id),
    stage_key INT REFERENCES dim_stage(stage_key),
    stage_status VARCHAR(10),      -- Completed | Dropped
    drop_type VARCHAR(10),         -- Abandoned | Stalled (when Dropped)
    application_date_key INT,
    PRIMARY KEY (application_id, stage_key)
);
