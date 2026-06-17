/*
  Computes monthly intake/outcome volume and net population flow for the shelter.
  - Reads from the silver layer directly rather than int_animal_stays on purpose: 
    capacity is about physical movement through the shelter, so every intake and 
    outcome event is counted independently. Matching events into stays (and 
    dropping unmatched ones) would undercount true throughput.
  - cumulative_net_population measures change since the start of data
    collection, NOT the shelter's true headcount; The source has no starting
    census, so treat the absolute value as relative, not literal.
  - The FULL OUTER JOIN means a month appears only if it had at least
    one intake or outcome. A month with zero of both would be absent entirely
    (a gap in the series), not a zero row. Verified: the actual distinct-month
    count equals the expected count across the full date range, so the series
    is gap-free and the running total never steps across missing time.
*/

WITH monthly_intakes AS (
    SELECT
        DATE_TRUNC('month', intake_date) AS month,
        COUNT(*) AS intakes
    FROM {{ ref('silver_intakes') }}
    GROUP BY DATE_TRUNC('month', intake_date)
),

monthly_outcomes AS (
    SELECT
        DATE_TRUNC('month', outcome_date) AS month,
        COUNT(*) AS outcomes
    FROM {{ ref('silver_outcomes') }}
    GROUP BY DATE_TRUNC('month', outcome_date)
),

combined AS (
    SELECT
        COALESCE(i.month, o.month) AS month,
        COALESCE(i.intakes, 0) AS intakes,
        COALESCE(o.outcomes, 0) AS outcomes
    FROM monthly_intakes i
    FULL OUTER JOIN monthly_outcomes o
        ON i.month = o.month
)

SELECT
    month,
    intakes,
    outcomes,
    intakes - outcomes AS net_flow,
    SUM(intakes - outcomes) OVER (ORDER BY month) AS cumulative_net_population
FROM combined
ORDER BY month