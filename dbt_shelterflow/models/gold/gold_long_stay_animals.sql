/*
  Identifies completed shelter stays that exceeded the long-stay threshold, for
  analysis of which animals/breeds/types tend toward extended shelter time.
  - "Long stay" is defined historically (completed stays over N days), NOT
    currently-in-shelter; The dataset ends in 2018, so a point-in-time "still
    present" view isn't meaningful here.
*/

WITH stays AS (
    SELECT *
    FROM {{ ref('int_animal_stays')}}
)

SELECT
    animal_id,
    animal_type,
    breed_standardized,
    age_group,
    intake_date,
    outcome_date,
    outcome_type,
    length_of_stay

FROM stays
WHERE length_of_stay >= 70 -- 70 days = 95th percentile of completed-stay length
ORDER BY length_of_stay DESC