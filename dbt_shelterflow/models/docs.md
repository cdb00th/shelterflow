{% docs __overview__ %}
# ShelterFlow

A dbt + DuckDB analytics project built on the Austin Animal Center public
intake and outcome dataset (through 2018). It models the flow of animals
through the shelter (arrivals, length of stay, and outcomes) and surfaces
analytical metrics on adoption, long-stay animals, and capacity trends.

## Architecture

The project follows a medallion layout:

- **bronze**: raw source data loaded as-is by `bronze_ingest.py`, no cleaning.
- **silver**: cleaned, typed, standardized intake and outcome records.
- **intermediate**: `int_animal_stays` pairs intakes to outcomes into a single
  stay grain, handling repeat visits and same-day sequencing.
- **gold**: analytics-ready models for adoption metrics, long-stay animals, and
  monthly capacity trends.

## Known limitations

- Same-day intake/outcome sequencing is nondeterministic for a small number of
  records (~12 of ~80k), where ordering within a single day cannot be resolved
  from the source. Documented inline and in the README.
- `cumulative_net_population` in `gold_capacity_trends` measures change since the
  start of data collection, not true shelter headcount. The source has no
  starting census.
{% enddocs %}

{% docs animal_id %}
Identifier for an individual animal; not unique within this table, as an animal
can appear in multiple rows. An animal with repeat shelter visits keeps one
animal_id across several intakes, outcomes, or stays.
{% enddocs %}

{% docs breed_standardized %}
Breed name. For cats and dogs, raw breed strings are collapsed to canonical
names: cross-breeds (slash-separated) are reduced to their primary breed and
suffixed " Mix", and select aliases are unified (e.g. Queensland Heeler resolves
to Australian Cattle Dog). "Black/Tan" is normalized to "Black-Tan" beforehand so
the slash in this Coonhound's name is not misread as a cross-breed separator. 
For other animal types, the original raw value is passed through unchanged.
{% enddocs %}

{% docs age_in_days %}
Age at intake, in days. Derived from `intake_date` relative to the animal's
recorded birth date, so it reflects age at arrival, not current age or age at
outcome.
{% enddocs %}

{% docs age_group %}
Life-stage bucket derived from `age_in_days`, for cats and dogs only.

- `Kitten` applies only to cats; `Puppy` only to dogs.
- Other life stages (`Young`, `Adult`, `Senior`) apply to both.

Because `age_in_days` uses approximate unit conversions (a month as 30 days,
a year as 365), boundary cases can shift by how the source recorded the age:
an animal logged as "12 months" (360 days) and one logged as "1 year"
(365 days) fall on opposite sides of the one-year cutoff.

Null for other animal types.
{% enddocs %}

{% docs outcome_type %}
How the animal's stay ended (e.g. adoption, transfer, return to owner, euthanasia).
{% enddocs %}

{% docs austin_source %}
Raw data from the Austin Animal Center public intake and outcome dataset.
Loaded as-is by bronze_ingest.py; no cleaning is applied at the bronze layer.
{% enddocs %}

{% docs length_of_stay %}
Days from intake to the paired outcome.
{% enddocs %}

{% docs intake_date %}
The date the animal arrived at the shelter.
{% enddocs %}

{% docs outcome_date %}
The date the animal left the shelter.
{% enddocs %}