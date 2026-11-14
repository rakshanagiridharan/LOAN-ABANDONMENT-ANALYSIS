# Loan Abandonment Analysis (Power BI, ETL, BRD) | 2026

A Python ETL pipeline cleans raw data (duplicates, missing channels, negative durations) and validates the output.

## The problem
Customers abandon the journey at specific stages, and the business lacks a consistent, trusted view of where, why and at what cost.

## The approach
Define requirements in a BRD, prepare reliable data through ETL, then build a dashboard that pinpoints drop-off stages and the segments driving them.

## What I built
- Business Requirements Document (BRD)
- ETL pipeline with data-quality checks
- SQL star schema, funnel and segmentation queries
- Power BI dashboard specification, DAX measures and Power Query load
- Recommendations to reduce drop-off

## Key results (5,000 applications, Jan 2025 to Jul 2026)
| Stage | Entered | Drop-off |
|---|---|---|
| Application Submitted | 5,000 | 7.2% |
| Documents Submitted | 4,638 | 10.2% |
| Verification Completed | 4,163 | **20.7%** |
| Approved | 3,300 | 6.4% |
| Disbursed | 3,088 | |

Conversion 61.8% | abandoned 7.2% | stalled 31.0%. Web abandons at 9.4% versus 5.8% in Branch; High Risk applicants at 17.4%.

## Repository
```
docs/
  BRD_Loan_Abandonment_Analysis.pdf   BRD (12 pages, one section per page)
  BRD_Loan_Abandonment_Analysis.md    same content in Markdown
  PROJECT_WALKTHROUGH.md              modules, tools, LLM usage, pain points, learnings
  recommendations.md                  recommendations to reduce drop-off
  data_dictionary.md, powerbi_dashboard_spec.md, build_brd.py
etl/etl_pipeline.py                   extract, clean, validate, model, load
sql/                                  star schema, analysis queries, run_queries.py
powerbi/                              measures.dax, powerquery_load.m
tests/                                test_etl.py, test_cleaning.py
data/raw/banking_loan_applications_5000.csv
```

## Run
```bash
pip install -r requirements.txt
python etl/etl_pipeline.py          # clean, validate, load; writes data/processed/ and dq_report.json
python tests/test_etl.py            # output checks
python tests/test_cleaning.py       # cleaning rules on deliberately dirty data
python sql/run_queries.py           # funnel and segmentation queries
python docs/build_brd.py            # optional: rebuild the BRD from the processed data
```
Then load `data/processed/*.csv` into Power BI and follow `docs/powerbi_dashboard_spec.md`.

## Limitations
The CSV is a snapshot with no per-stage timestamps, so time analysis uses `Processing_Days`. The last month (2026-07) is partial and excluded from trends.
