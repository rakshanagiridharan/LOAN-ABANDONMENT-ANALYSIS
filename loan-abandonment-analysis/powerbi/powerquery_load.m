// Power Query (M). Create a parameter first:
//   ProcessedPath = "C:\path\to\loan-abandonment-analysis\data\processed\"
// Repeat for fact_stage_progress, dim_stage, dim_date (change file name and types).
let
    Source   = Csv.Document(File.Contents(ProcessedPath & "fact_applications.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"application_date", type date}, {"decision_date", type date}, {"application_date_key", Int64.Type},
        {"age", Int64.Type}, {"monthly_income_inr", type number}, {"credit_score", Int64.Type},
        {"loan_amount_inr", type number}, {"processing_days", type number},
        {"is_abandoned", Int64.Type}, {"is_stalled", Int64.Type}, {"is_disbursed", Int64.Type},
        {"furthest_stage_order", Int64.Type}, {"is_partial_month", Int64.Type}})
in
    Typed
