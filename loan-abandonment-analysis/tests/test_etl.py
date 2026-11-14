"""Run after the ETL:  python tests/test_etl.py"""
import pandas as pd

fact = pd.read_csv("data/processed/fact_applications.csv")
stage = pd.read_csv("data/processed/fact_stage_progress.csv")
agg = pd.read_csv("data/processed/agg_funnel.csv")

assert fact["application_id"].is_unique
assert set(fact["outcome"]) == {"Disbursed", "Abandoned", "Stalled"}
assert (fact["is_abandoned"] + fact["is_stalled"] + fact["is_disbursed"] == 1).all()
assert fact.loc[fact.is_abandoned == 1, "abandonment_reason"].notna().all()
assert fact.loc[fact.is_abandoned == 0, "abandonment_reason"].isna().all()
assert (agg["completed"] + agg["dropped"] == agg["entered"]).all()
assert agg["entered"].is_monotonic_decreasing
assert agg.loc[agg.stage_key == 1, "entered"].iloc[0] == len(fact)
assert stage.groupby("application_id").size().min() >= 1
print("All ETL tests passed.")
