{{ config(materialized='table') }}

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

    -- Standardize breed names
    CASE
        -- Cross-breeds
        WHEN breed LIKE '%/%' THEN SPLIT_PART(breed, '/', 1) || ' Mix'

        -- Standardize American Pit Bull Terrier to Pit Bull
        WHEN LOWER(breed) LIKE '%american pit bull terrier%' AND LOWER(breed) LIKE '%mix%' THEN 'Pit Bull Mix'
        WHEN LOWER(breed) LIKE '%american pit bull terrier%' THEN 'Pit Bull'

        -- Standardize Queensland Heeler to Australian Cattle Dog
        WHEN LOWER(breed) LIKE '%queensland heeler%' AND LOWER(breed) LIKE '%mix%' THEN 'Australian Cattle Dog Mix'
        WHEN LOWER(breed) LIKE '%queensland heeler%' THEN 'Australian Cattle Dog'

        -- Standardize Oriental Sh Mix to Oriental Shorthair Mix 
        WHEN LOWER(breed) LIKE '%oriental sh mix%' THEN 'Oriental Shorthair Mix'

        ELSE breed
    END AS breed_standardized,

    -- Convert age_upon_intake into age_in_days
    CASE
        WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('year', 'years') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER) * 365
        WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('month', 'months') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER) * 30
        WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('week', 'weeks') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER) * 7
        WHEN LOWER(SPLIT_PART(age_upon_intake, ' ', 2)) IN ('day', 'days') THEN CAST(SPLIT_PART(age_upon_intake, ' ', 1) AS INTEGER)
        
        ELSE NULL
    END AS age_in_days,

    -- Create age_group buckets based on age_in_days value
    CASE
        WHEN animal_type = 'Dog' AND age_in_days < 365 THEN 'Puppy'
        WHEN animal_type = 'Cat' AND age_in_days < 365 THEN 'Kitten'

        WHEN animal_type IN ('Dog', 'Cat') AND age_in_days < 1095 THEN 'Young'
        WHEN animal_type IN ('Dog', 'Cat') AND age_in_days < 2920 THEN 'Adult'
        WHEN animal_type IN ('Dog', 'Cat') AND age_in_days >= 2920 THEN 'Senior'

        ELSE NULL
    END AS age_group,

    -- Normalize dates
    CAST(STRPTIME(datetime, '%Y-%m-%dT%H:%M:%S.%f') AS DATE) AS intake_date
FROM {{source('bronze', 'bronze_intakes')}}