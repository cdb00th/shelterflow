{% docs animal_id %}
Identifier for an individual animal; not unique within this table, as an animal
can appear in multiple rows. An animal with repeat shelter visits keeps one
animal_id across several intakes, outcomes, or stays.
{% enddocs %}

{% docs breed_standardized %}
Breed name. For cats and dogs, raw breed strings are collapsed to canonical
names; for other animal types, the original raw value is passed through
unchanged.
{% enddocs %}

{% docs age_in_days %}
Age at intake in days. 
{% enddocs %}

{% docs age_group %}
Life-stage bucket derived from `age_in_days`, for cats and dogs only.

- `Kitten` applies only to cats; `Puppy` only to dogs.
- Other life stages (`Young`, `Adult`, `Senior`) apply to both.

Null for other animal types.
{% enddocs %}

{% docs outcome_type %}
How the animal's stay ended (e.g. adoption, transfer, return to owner).
See the `accepted_values` test for the authoritative list of categories.
{% enddocs %}

{% docs austin_source %}
Raw data from the Austin Animal Center public intake and outcome dataset.
Loaded as-is by bronze_ingest.py; no cleaning is applied at the bronze layer.
{% enddocs %}