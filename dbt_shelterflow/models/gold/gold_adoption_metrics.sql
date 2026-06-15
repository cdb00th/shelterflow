/*
  Computes adoption rate and average days-to-adoption for each (animal_type, breed_standardized) segment, 
  dogs and cats only, for the dashboard.
  - Scoped to Dog/Cat: adoption analysis; breed_standardized only applies to cats and dogs (wildlife/other
    pass through raw and aren't adoption-relevant).
  - Rto-Adopt is treatment as a non-adoption (owner reunification, not placement).
  - avg_days_to_adoption covers adopted animals only; NULL where a segment had none.
  - Segments with fewer than 10 completed stays are dropped (small-sample noise).
*/

WITH stays AS (
    SELECT *
    FROM {{ ref('int_animal_stays') }}
)

SELECT
    animal_type,
    breed_standardized,

    COUNT(*) AS total_stays,

    SUM(CASE WHEN outcome_type = 'Adoption' THEN 1 ELSE 0 END) AS adoptions,

    ROUND(
        SUM(CASE WHEN outcome_type = 'Adoption' THEN 1 ELSE 0 END)::DECIMAL
        / COUNT(*),
        3
    ) AS adoption_rate,

    ROUND(AVG(CASE WHEN outcome_type = 'Adoption' THEN length_of_stay END), 1) AS avg_days_to_adoption

FROM stays
WHERE animal_type IN ('Dog', 'Cat')
GROUP BY animal_type, breed_standardized
HAVING COUNT(*) >= 10
ORDER BY total_stays DESC