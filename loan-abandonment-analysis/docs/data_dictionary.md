# Data Dictionary
Source: `banking_loan_applications_5000.csv` (5,000 rows, 22 columns). Derived fields are produced by `etl/etl_pipeline.py`.

## fact_applications (grain: one row per application)
| Column | Source / Derived | Description |
|---|---|---|
| application_id | Source | Unique application ID (PK) |
| customer_id | Source | Pseudonymised customer ID (mask in drill-through) |
| application_date, decision_date | Source | Parsed from m/d/yyyy |
| application_month | Source | yyyy-mm. The last month (2026-07) is partial |
| age, age_group | Source | Age and band (21-29 ... 60+) |
| employment_type | Source | Salaried, Self-Employed, Government, Contract, Unemployed |
| monthly_income_inr, income_band | Source | Monthly income and band |
| credit_score, credit_risk_band | Source | Score and band (High Risk ... Excellent) |
| loan_type | Source | Personal, Home, Auto, Business, Education |
| loan_amount_inr | Source | Requested amount in INR |
| channel, region | Source | Web, Mobile App, Branch, Agent / North, South, East, West, Central |
| documents_submitted, verification_completed | Source | Yes / No flags |
| approval_status | Source | Abandoned, Documents Submitted, Under Review, Approved, Disbursed |
| disbursed | Source | Yes / No |
| processing_days | Source | Days in processing |
| abandonment_reason | Source (cleaned) | 'N/A' converted to null; populated only for Abandoned |
| application_date_key, application_quarter, is_partial_month | Derived | Date key, quarter, partial-month flag |
| loan_amount_band | Derived | <5L, 5-15L, 15-30L, 30-50L, 50L+ |
| processing_band | Derived | 0-3, 3-6, 6-9, 9-12, 12+ days |
| furthest_stage_order / _name | Derived | Furthest funnel stage reached (1-5) |
| outcome | Derived | Disbursed, Abandoned, or Stalled |
| is_disbursed, is_abandoned, is_stalled | Derived | 0/1 flags (mutually exclusive) |
| dropoff_stage_order / _name | Derived | Stage where journey stopped (null if disbursed) |
| reason_group | Derived | Process Friction, Pricing & Eligibility, Customer Choice |

## fact_stage_progress (grain: application x stage reached)
`application_id`, `stage_key` (1-5), `stage_status` (Completed / Dropped), `drop_type` (Abandoned / Stalled), `application_date_key`.

## dim_stage
`stage_key`, `stage_name`, `stage_group` (Intake, Processing, Closing). Stages: Application Submitted, Documents Submitted, Verification Completed, Approved, Disbursed.

## dim_date
`date_key`, `date`, `year`, `quarter`, `month_num`, `month_name`, `year_month`, `week_of_year`, `day_name`, `is_weekend`.

## agg_funnel (reconciliation reference)
`stage_key`, `entered`, `completed`, `dropped`, `stage_name`, `stage_group`, `dropoff_rate`, `cumulative_conversion`.

## Rules applied in ETL (all counts logged in `dq_report.json`)
Duplicate application IDs removed; dates parsed; 'N/A' reason to null; loan amount > 0; Decision_Date >= Application_Date; credit band, month and status-flag consistency checks; funnel reconciliation.
