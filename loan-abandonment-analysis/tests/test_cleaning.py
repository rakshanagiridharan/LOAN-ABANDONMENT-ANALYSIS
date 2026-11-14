"""
Proves the cleaning rules work on deliberately dirty data
(the real CSV happens to be clean, so it never exercises them).

Run from repo root:  python tests/test_cleaning.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etl"))
import etl_pipeline as etl  # noqa: E402


def row(app_id, **kw):
    base = dict(
        application_id=app_id, customer_id="C1", application_date="1/10/2025", decision_date="1/15/2025",
        age=35, employment_type="Salaried", monthly_income_inr=50000, credit_score=700, loan_type="Personal Loan",
        loan_amount_inr=500000, channel="Web", region="South", documents_submitted="Yes",
        verification_completed="Yes", approval_status="Disbursed", disbursed="Yes", processing_days=5.0,
        abandonment_reason="N/A", age_group="30-39", income_band="30K-60K", credit_risk_band="Good",
        application_month="2025-01")
    base.update(kw)
    return base


dirty = pd.DataFrame([
    row("A1"),
    row("A1"),                                               # duplicate application_id
    row("A2", channel=None),                                 # missing channel
    row("A3", channel="  web "),                             # whitespace + casing
    row("A4", processing_days=-3.0),                         # negative processing time
    row("A5", decision_date="1/5/2025"),                     # decision before application (negative duration)
    row("A6", loan_amount_inr=-100),                         # invalid amount
])

clean = etl.clean(dirty)
dq = etl.dq

assert len(clean) == 5, f"expected 5 rows after dedupe + invalid amount removal, got {len(clean)}"
assert clean["application_id"].is_unique
assert dq["duplicate_application_ids_removed"] == 1
assert dq["missing_channel_set_unknown"] == 1
assert clean.loc[clean.application_id == "A2", "channel"].iloc[0] == "Unknown"
assert clean.loc[clean.application_id == "A3", "channel"].iloc[0] == "Web"
assert dq["negative_processing_days_nulled"] == 1
assert np.isnan(clean.loc[clean.application_id == "A4", "processing_days"].iloc[0])
assert dq["negative_duration_decision_before_application"] == 1
assert pd.isna(clean.loc[clean.application_id == "A5", "decision_date"].iloc[0])
assert dq["invalid_loan_amount_removed"] == 1

derived = etl.derive(clean)            # derivation must survive the nulls left by cleaning
assert (derived["is_abandoned"] + derived["is_stalled"] + derived["is_disbursed"] == 1).all()
assert derived.loc[derived.application_id == "A4", "processing_band"].iloc[0] == "Unknown"
print("Cleaning tests passed: duplicates, missing channel, negative durations, invalid amounts.")
