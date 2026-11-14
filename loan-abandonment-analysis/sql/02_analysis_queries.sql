-- 1. Funnel with drop-off rate
SELECT s.stage_key, s.stage_name, COUNT(*) AS entered,
       SUM(CASE WHEN p.stage_status='Completed' THEN 1 ELSE 0 END) AS completed,
       SUM(CASE WHEN p.stage_status='Dropped'   THEN 1 ELSE 0 END) AS dropped,
       ROUND(1.0*SUM(CASE WHEN p.stage_status='Dropped' THEN 1 ELSE 0 END)/COUNT(*),4) AS dropoff_rate
FROM fact_stage_progress p JOIN dim_stage s ON s.stage_key = p.stage_key
GROUP BY s.stage_key, s.stage_name ORDER BY s.stage_key;

-- 2. Outcome split
SELECT outcome, COUNT(*) AS apps, ROUND(1.0*COUNT(*)/(SELECT COUNT(*) FROM fact_applications),4) AS share
FROM fact_applications GROUP BY outcome;

-- 3. Abandonment & conversion by channel
SELECT channel, COUNT(*) AS apps, ROUND(AVG(is_abandoned),4) AS abandonment_rate, ROUND(AVG(is_disbursed),4) AS conversion_rate
FROM fact_applications GROUP BY channel ORDER BY abandonment_rate DESC;

-- 4. Credit-risk view (abandonment, stalled, conversion)
SELECT credit_risk_band, COUNT(*) AS apps, ROUND(AVG(is_abandoned),4) AS abandonment_rate,
       ROUND(AVG(is_stalled),4) AS stalled_rate, ROUND(AVG(is_disbursed),4) AS conversion_rate
FROM fact_applications GROUP BY credit_risk_band ORDER BY abandonment_rate DESC;

-- 5. Abandonment by processing-time band
SELECT processing_band, COUNT(*) AS apps, ROUND(AVG(is_abandoned),4) AS abandonment_rate
FROM fact_applications GROUP BY processing_band ORDER BY processing_band;

-- 6. Reasons (abandoned only), with group
SELECT reason_group, abandonment_reason, COUNT(*) AS abandoned_apps,
       ROUND(1.0*COUNT(*)/SUM(COUNT(*)) OVER (),4) AS share
FROM fact_applications WHERE is_abandoned = 1 GROUP BY reason_group, abandonment_reason ORDER BY abandoned_apps DESC;

-- 7. Lost loan value in Rs Crore, by loan type
SELECT loan_type, ROUND(SUM(loan_amount_inr)/10000000.0,2) AS lost_value_cr
FROM fact_applications WHERE is_abandoned = 1 GROUP BY loan_type ORDER BY lost_value_cr DESC;

-- 8. Monthly trend (exclude partial month)
SELECT d.year_month, ROUND(AVG(a.is_abandoned),4) AS abandonment_rate, ROUND(AVG(a.is_disbursed),4) AS conversion_rate
FROM fact_applications a JOIN dim_date d ON d.date_key = a.application_date_key
WHERE a.is_partial_month = 0 GROUP BY d.year_month ORDER BY d.year_month;
