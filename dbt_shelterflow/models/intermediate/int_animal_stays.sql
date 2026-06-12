/*
  Handles animals with multiple distinct shelter stays. Each intake is
  paired to its next outcome on/after the intake date.
  Intakes with no later outcome are dropped, as there is no completed 
  stay to measure.
*/

WITH int_intakes AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY animal_id ORDER BY intake_date) AS intake_seq
    FROM {{ ref('silver_intakes') }}
),

int_outcomes AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY animal_id ORDER BY outcome_date) AS outcome_seq
    FROM {{ ref('silver_outcomes')}}
), 

paired AS (
    SELECT
        i.animal_id,
        i.animal_type,
        i.breed_standardized,
        i.age_group,
        i.intake_date,
        i.intake_seq,
        o.outcome_date,
        o.outcome_type,
        o.outcome_subtype,
        o.outcome_date - i.intake_date AS length_of_stay,   

        -- earliest outcome for this specific intake
        ROW_NUMBER() OVER (
            PARTITION BY i.animal_id, i.intake_seq
            ORDER BY o.outcome_date
        ) AS outcome_rank,

        -- latest intake for this specific outcome
        ROW_NUMBER() OVER (
            PARTITION BY o.animal_id, o.outcome_date, o.outcome_seq
            ORDER BY i.intake_date DESC, i.intake_seq DESC
        ) AS intake_rank

    FROM int_intakes i
    JOIN int_outcomes o
        ON i.animal_id = o.animal_id
        AND o.outcome_date >= i.intake_date
)

SELECT
    animal_id, 
    animal_type, 
    breed_standardized, 
    age_group,
    intake_date, 
    outcome_date, 
    outcome_type, 
    outcome_subtype, 
    length_of_stay
FROM paired
WHERE outcome_rank = 1 AND intake_rank = 1
