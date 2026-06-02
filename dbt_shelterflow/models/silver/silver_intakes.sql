-- Standardize breeds
SELECT animal_id, breed
    CASE
        -- Cross-breeds
        WHEN breed LIKE '%/%' THEN INITCAP(SPLIT_PART(LOWER(breed), '/', 1)) || ' Mix'

        -- Standardize American Pit Bull Terrier to Pit Bull
        WHEN LOWER(breed) LIKE '%american pit bull terrier%' AND LOWER(breed) LIKE '%mix%' THEN 'Pit Bull Mix'
        WHEN LOWER(breed) LIKE '%american pit bull terrier%' THEN 'Pit Bull'

        -- Standardize Queensland Heeler to Australian Cattle Dog
        WHEN LOWER(breed) LIKE '%queensland heeler%' AND LOWER(breed) LIKE '%mix%' THEN 'Australian Cattle Dog Mix'
        WHEN LOWER(breed) LIKE '%queensland heeler%' THEN 'Australian Cattle Dog'

        -- Standardize Oriental Sh Mix to Oriental Shorthair Mix 
        WHEN LOWER(breed) LIKE '%oriental sh mix%' THEN 'Oriental Shorthair Mix'

        ELSE breed
    END AS breed_standardized
FROM {{source('bronze', 'bronze_intakes')}}