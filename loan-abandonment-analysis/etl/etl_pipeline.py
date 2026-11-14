"""
ETL pipeline: banking_loan_applications_5000.csv -> star schema for Power BI.

  Extract   : read the raw application extract
  Transform : clean, validate, derive funnel stages / outcome / abandonment flags, build dims + facts
  Load      : processed CSVs (Power BI source) + SQLite DB + data-quality report

Run from the repo root:  python etl/etl_pipeline.py
"""
import json
import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/banking_loan_applications_5000.csv")
OUT = Path("data/processed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("etl")
dq = {}

STAGES = [
    (1, "Application Submitted", "Intake"),
    (2, "Documents Submitted", "Intake"),
    (3, "Verification Completed", "Processing"),
    (4, "Approved", "Processing"),
    (5, "Disbursed", "Closing"),
]
STATUS_TO_FURTHEST = {          # Approval_Status -> furthest stage reached
    "Abandoned": 1, "Documents Submitted": 2, "Under Review": 3, "Approved": 4, "Disbursed": 5,
}
CREDIT_BANDS = [(0, 579, "High Risk"), (580, 669, "Moderate Risk"), (670, 739, "Good"),
                (740, 799, "Very Good"), (800, 900, "Excellent")]


# ------------------------------------------------------------------ EXTRACT
def extract():
    df = pd.read_csv(RAW)
    dq["raw_rows"], dq["raw_columns"] = len(df), df.shape[1]
    log.info("Extracted %s rows x %s columns", f"{len(df):,}", df.shape[1])
    return df


# ---------------------------------------------------------------- TRANSFORM
def clean(df):
    """Cleaning rules. Every rule logs how many rows it touched into the data-quality report (dq)."""
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # 1. Duplicates: one row per application_id
    n0 = len(df)
    df = df.drop_duplicates(subset="application_id", keep="first")
    dq["duplicate_application_ids_removed"] = n0 - len(df)

    # 2. Text hygiene: trim whitespace, standardise casing on categorical fields
    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].astype("string").str.strip()
    for c in ["channel", "region", "loan_type", "employment_type"]:
        df[c] = df[c].str.title()

    # 3. Missing channel -> "Unknown" (kept in the data, visible in the dashboard)
    missing_channel = df["channel"].isna() | df["channel"].isin(["", "Nan", "None", "N/A"])
    dq["missing_channel_set_unknown"] = int(missing_channel.sum())
    df.loc[missing_channel, "channel"] = "Unknown"

    # 4. Dates: parse, then treat impossible ordering as a negative duration
    df["application_date"] = pd.to_datetime(df["application_date"], format="%m/%d/%Y", errors="coerce")
    df["decision_date"] = pd.to_datetime(df["decision_date"], format="%m/%d/%Y", errors="coerce")
    dq["unparseable_dates"] = int(df[["application_date", "decision_date"]].isna().any(axis=1).sum())
    df = df.dropna(subset=["application_date"])

    neg_dates = df["decision_date"] < df["application_date"]
    dq["negative_duration_decision_before_application"] = int(neg_dates.sum())
    df.loc[neg_dates, "decision_date"] = pd.NaT

    # 5. Negative processing time -> null (not silently abs()-ed), counted in the report
    df["processing_days"] = pd.to_numeric(df["processing_days"], errors="coerce")
    neg_days = df["processing_days"] < 0
    dq["negative_processing_days_nulled"] = int(neg_days.sum())
    df.loc[neg_days, "processing_days"] = np.nan

    dq["null_counts_after_basic_cleaning"] = {k: int(v) for k, v in df.isna().sum().items() if v}

    # 6. 'N/A' in abandonment_reason means "not abandoned" -> true null
    df["abandonment_reason"] = df["abandonment_reason"].replace({"N/A": pd.NA, "": pd.NA})

    # 7. Invalid amounts
    bad_amt = (df["loan_amount_inr"] <= 0) | df["loan_amount_inr"].isna()
    dq["invalid_loan_amount_removed"] = int(bad_amt.sum())
    df = df[~bad_amt]

    # 8. Consistency checks against stated bands / flags (reported, not silently altered)
    def band(score):
        for lo, hi, name in CREDIT_BANDS:
            if lo <= score <= hi:
                return name
        return "Unknown"
    dq["credit_band_mismatch_vs_score"] = int((df["credit_score"].apply(band) != df["credit_risk_band"]).sum())
    dq["application_month_mismatch"] = int(
        (df["application_date"].dt.strftime("%Y-%m") != df["application_month"]).sum())
    dq["abandoned_without_reason"] = int(
        ((df["approval_status"] == "Abandoned") & df["abandonment_reason"].isna()).sum())
    dq["reason_on_non_abandoned"] = int(
        ((df["approval_status"] != "Abandoned") & df["abandonment_reason"].notna()).sum())
    dq["status_flag_conflicts"] = int((
        ((df["approval_status"] == "Disbursed") != (df["disbursed"] == "Yes")) |
        ((df["approval_status"] == "Abandoned") & (df["documents_submitted"] == "Yes"))).sum())
    return df


def derive(df):
    df = df.copy()
    df["furthest_stage_order"] = df["approval_status"].map(STATUS_TO_FURTHEST)
    assert df["furthest_stage_order"].notna().all(), "Unmapped approval_status value"
    stage_names = {k: n for k, n, _ in STAGES}
    df["furthest_stage_name"] = df["furthest_stage_order"].map(stage_names)

    df["outcome"] = np.select(
        [df["approval_status"] == "Disbursed", df["approval_status"] == "Abandoned"],
        ["Disbursed", "Abandoned"], default="Stalled")
    df["is_disbursed"] = (df["outcome"] == "Disbursed").astype(int)
    df["is_abandoned"] = (df["outcome"] == "Abandoned").astype(int)
    df["is_stalled"] = (df["outcome"] == "Stalled").astype(int)

    # Stage where the journey stopped (not disbursed)
    df["dropoff_stage_order"] = np.where(df["is_disbursed"] == 0, df["furthest_stage_order"], np.nan)
    df["dropoff_stage_name"] = np.where(df["is_disbursed"] == 0, df["furthest_stage_name"], None)

    df["abandonment_reason"] = df["abandonment_reason"].where(df["is_abandoned"] == 1)
    df["reason_group"] = df["abandonment_reason"].map({
        "Complex Documentation": "Process Friction", "Long Processing Time": "Process Friction",
        "Technical Issue": "Process Friction", "High Interest Rate": "Pricing & Eligibility",
        "Eligibility Concern": "Pricing & Eligibility", "Changed Mind": "Customer Choice",
        "Other": "Customer Choice"})

    df["loan_amount_band"] = pd.cut(
        df["loan_amount_inr"], bins=[0, 500_000, 1_500_000, 3_000_000, 5_000_000, np.inf],
        labels=["<5L", "5-15L", "15-30L", "30-50L", "50L+"]).astype(str)
    df["processing_band"] = pd.cut(
        df["processing_days"], bins=[-0.01, 3, 6, 9, 12, np.inf],
        labels=["0-3 days", "3-6 days", "6-9 days", "9-12 days", "12+ days"]).astype(object)
    df["processing_band"] = df["processing_band"].fillna("Unknown")
    df["application_date_key"] = df["application_date"].dt.strftime("%Y%m%d").astype(int)
    df["application_quarter"] = df["application_date"].dt.to_period("Q").astype(str)
    df["is_partial_month"] = (df["application_month"] == df["application_month"].max()).astype(int)
    return df


def build_model(df):
    fact = df.rename(columns={"monthly_income_inr": "monthly_income_inr"}).copy()

    dim_stage = pd.DataFrame(STAGES, columns=["stage_key", "stage_name", "stage_group"])

    dates = pd.date_range(df["application_date"].min().normalize(), df["application_date"].max().normalize())
    dim_date = pd.DataFrame({"date": dates})
    dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"], dim_date["quarter"] = dim_date["date"].dt.year, dim_date["date"].dt.quarter
    dim_date["month_num"], dim_date["month_name"] = dim_date["date"].dt.month, dim_date["date"].dt.strftime("%b")
    dim_date["year_month"] = dim_date["date"].dt.strftime("%Y-%m")
    dim_date["week_of_year"] = dim_date["date"].dt.isocalendar().week.astype(int)
    dim_date["day_name"] = dim_date["date"].dt.day_name()
    dim_date["is_weekend"] = dim_date["date"].dt.dayofweek.ge(5).astype(int)

    # One row per application per stage reached
    rows = []
    for stage_key, _, _ in STAGES:
        reached = df[df["furthest_stage_order"] >= stage_key][
            ["application_id", "application_date_key", "furthest_stage_order", "outcome"]].copy()
        reached["stage_key"] = stage_key
        reached["stage_status"] = np.where(reached["furthest_stage_order"] > stage_key, "Completed",
                                   np.where(reached["outcome"] == "Disbursed", "Completed", "Dropped"))
        reached["drop_type"] = np.where(reached["stage_status"] == "Dropped", reached["outcome"], None)
        rows.append(reached[["application_id", "stage_key", "stage_status", "drop_type", "application_date_key"]])
    fact_stage = pd.concat(rows, ignore_index=True)

    g = fact_stage.groupby("stage_key")
    agg = pd.DataFrame({
        "entered": g.size(),
        "completed": g["stage_status"].apply(lambda s: (s == "Completed").sum()),
        "dropped": g["stage_status"].apply(lambda s: (s == "Dropped").sum()),
    }).reset_index().merge(dim_stage, on="stage_key")
    agg["dropoff_rate"] = (agg["dropped"] / agg["entered"]).round(4)
    agg["cumulative_conversion"] = (agg["completed"] / agg.loc[0, "entered"]).round(4)
    return fact, fact_stage, dim_stage, dim_date, agg


def validate(fact, fact_stage, agg):
    assert fact["application_id"].is_unique
    assert (fact["is_abandoned"] + fact["is_disbursed"] + fact["is_stalled"] == 1).all()
    assert (agg["completed"] + agg["dropped"] == agg["entered"]).all()
    assert agg["entered"].is_monotonic_decreasing
    assert agg.loc[agg.stage_key == 5, "completed"].iloc[0] == fact["is_disbursed"].sum()
    dq["validation"] = "PASSED"
    dq["outcome_counts"] = fact["outcome"].value_counts().to_dict()
    dq["clean_rows"] = len(fact)
    log.info("Validation checks passed")


# --------------------------------------------------------------------- LOAD
def load(fact, fact_stage, dim_stage, dim_date, agg):
    OUT.mkdir(parents=True, exist_ok=True)
    tables = {"fact_applications": fact, "fact_stage_progress": fact_stage,
              "dim_stage": dim_stage, "dim_date": dim_date, "agg_funnel": agg}
    for name, t in tables.items():
        t.to_csv(OUT / f"{name}.csv", index=False)
    with sqlite3.connect(OUT / "loan_abandonment.db") as con:
        for name, t in tables.items():
            t.to_sql(name, con, if_exists="replace", index=False)
    (OUT / "dq_report.json").write_text(json.dumps(dq, indent=2, default=str))
    log.info("Loaded %d tables to %s", len(tables), OUT)


def main():
    raw = extract()
    cleaned = clean(raw)
    derived = derive(cleaned)
    fact, fact_stage, dim_stage, dim_date, agg = build_model(derived)
    validate(fact, fact_stage, agg)
    load(fact, fact_stage, dim_stage, dim_date, agg)
    print("\nFunnel summary:\n", agg[["stage_name", "entered", "completed", "dropped", "dropoff_rate",
                                       "cumulative_conversion"]].to_string(index=False))
    print(f"\nAbandonment rate: {fact['is_abandoned'].mean():.2%} | "
          f"Stalled: {fact['is_stalled'].mean():.2%} | Disbursed: {fact['is_disbursed'].mean():.2%}")


if __name__ == "__main__":
    main()
