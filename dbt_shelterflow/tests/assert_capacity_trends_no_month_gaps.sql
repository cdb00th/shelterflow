/*
  Fails if the monthly series has any gaps: a month with zero intakes AND zero
  outcomes is absent entirely from gold_capacity_trends (the FULL OUTER JOIN
  can't produce it), which would let cumulative_net_population step across
  missing time. Returns a row only when actual month count != expected count
  across the full date range, which dbt treats as a failure.
*/

WITH bounds AS (
    SELECT
        COUNT(*) AS actual_months,
        DATE_DIFF('month', MIN(month), MAX(month)) + 1 AS expected_months
    FROM {{ ref('gold_capacity_trends') }}
)
SELECT *
FROM bounds
WHERE actual_months <> expected_months