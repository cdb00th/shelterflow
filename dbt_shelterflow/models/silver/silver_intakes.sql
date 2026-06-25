/*
  Cleans `bronze_intakes` data by:
  - Standardizing breed names
  - Creating age group buckets
  - Normalizing date values
 */

WITH cleaned AS (
    SELECT
        animal_id,
        animal_type,
        intake_type,
        intake_condition,
        sex_upon_intake,
        age_upon_intake,
        found_location,
        color,
        name,
        breed,
        datetime,
        REPLACE(breed, 'Black/Tan', 'Black-Tan') AS breed_cleaned,

        CASE
            WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('year', 'years') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER) * 365
            WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('month', 'months') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER) * 30
            WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('week', 'weeks') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER) * 7
            WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('day', 'days') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER)    
            ELSE NULL
        END AS age_in_days

    FROM {{ source('bronze', 'bronze_intakes') }}
)

SELECT DISTINCT
    animal_id,
    animal_type,
    intake_type,
    intake_condition,
    sex_upon_intake,
    age_upon_intake,
    found_location,
    color,
    name,
    breed,
    breed_cleaned,
    age_in_days,

    CASE
        -- Standardize cross-breeds as mixes
        WHEN breed_cleaned LIKE '%/%' THEN SPLIT_PART(breed_cleaned, '/', 1) || ' Mix'

        WHEN LOWER(breed_cleaned) LIKE '%american pit bull terrier%' AND LOWER(breed_cleaned) LIKE '%mix%' THEN 'Pit Bull Mix'
        WHEN LOWER(breed_cleaned) LIKE '%american pit bull terrier%' THEN 'Pit Bull'

        WHEN LOWER(breed_cleaned) LIKE '%queensland heeler%' AND LOWER(breed_cleaned) LIKE '%mix%' THEN 'Australian Cattle Dog Mix'
        WHEN LOWER(breed_cleaned) LIKE '%queensland heeler%' THEN 'Australian Cattle Dog'

        WHEN LOWER(breed_cleaned) LIKE '%oriental sh mix%' THEN 'Oriental Shorthair Mix'

        ELSE breed_cleaned
    END AS breed_standardized,

    CASE
        -- Specialized age_group values for baby dogs and cats
        WHEN animal_type = 'Dog' AND age_in_days < 365 THEN 'Puppy'
        WHEN animal_type = 'Cat' AND age_in_days < 365 THEN 'Kitten'

        WHEN animal_type IN ('Dog', 'Cat') AND age_in_days < 1095 THEN 'Young'
        WHEN animal_type IN ('Dog', 'Cat') AND age_in_days < 2920 THEN 'Adult'
        WHEN animal_type IN ('Dog', 'Cat') AND age_in_days >= 2920 THEN 'Senior'

        ELSE NULL 
    END AS age_group,

    CAST(STRPTIME(datetime, '%Y-%m-%dT%H:%M:%S.%f') AS DATE) AS intake_date -- Normalize datetime to date, as time is unneeded for gold layer analysis
FROM cleaned