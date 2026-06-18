# ShelterFlow

An analytics engineering project that models the flow of animals through the
Austin Animal Center, arrivals, length of stay, and outcomes, using a dbt +
DuckDB medallion pipeline. It turns two raw, messy public CSVs into tested,
documented, analytics-ready tables for adoption, long-stay, and shelter-capacity
analysis.

This repository is the **MVP**: the data pipeline is complete from raw ingestion
through the gold analytics layer, with tests and documentation throughout, and a
Streamlit dashboard reads the gold models for interactive exploration.

## Why this project

Animal shelters generate exactly the kind of operational event data that rewards
careful modeling: the same animal can appear many times, "intake" and "outcome"
are separate event streams that have to be matched into stays, and naive joins
silently fan out. ShelterFlow treats those problems as the point, every
non-obvious modeling decision is documented in-code and tested rather than
hand-waved.

## Tech stack

| Layer | Tool |
|-------|------|
| Transformation | dbt Core 1.11.11 |
| Warehouse / engine | DuckDB (file-based, `data/shelterflow.duckdb`) |
| Adapter | dbt-duckdb 1.10.1 |
| Testing packages | dbt_utils, dbt_expectations |
| Dashboard | Streamlit, Altair |
| Ingestion / EDA | Python (pandas, duckdb), Jupyter |

Using DuckDB keeps the whole warehouse in a single local file, so the project
clones and runs end-to-end with no cloud credentials or external database.

## Architecture

ShelterFlow follows a medallion layout. Each layer has a single, well-scoped
responsibility:

- **bronze**: raw Austin Animal Center intake and outcome records, loaded
  as-is by `pipelines/bronze_ingest.py`. No cleaning; this is the immutable
  source of truth.
- **silver**: `silver_intakes` and `silver_outcomes`. Deduplicated, typed, and
  standardized: breed strings collapsed to canonical names (for cats and dogs),
  ages parsed from free text into `age_in_days`, life-stage `age_group` buckets
  derived, and datetimes normalized to dates.
- **intermediate**: `int_animal_stays`. Pairs each intake to its next outcome
  on or after the intake date, producing one row per completed stay. Handles
  repeat visitors and resolves a join fan-out that would otherwise let two
  same-day intakes both claim a single outcome.
- **gold**: analytics-ready models the dashboard and any downstream consumer
  read from. The Streamlit dashboard reads exclusively from this layer.

```
bronze_intakes / bronze_outcomes
            │
            ▼
silver_intakes / silver_outcomes      ← clean, typed, standardized
            │
            ▼
      int_animal_stays                ← one row per completed stay
            │
            ▼
gold_adoption_metrics
gold_long_stay_animals
gold_capacity_trends
```

### Gold models

- **`gold_adoption_metrics`**: adoption rate and average days-to-adoption per
  `(animal_type, breed_standardized)` segment. Scoped to dogs and cats, treats
  `Rto-Adopt` as a non-adoption, and drops segments with fewer than 10 completed
  stays to keep rates from being dominated by small-sample noise.
- **`gold_long_stay_animals`**: completed stays at or above the long-stay
  threshold of 70 days (the ~95th percentile of stay length in this dataset),
  for analysis of which animals, breeds, and types trend toward extended shelter
  time.
- **`gold_capacity_trends`**: monthly intake/outcome volume, net flow, and a
  cumulative net-population running total. Reads the silver layer directly rather
  than `int_animal_stays`, because capacity is about physical movement through
  the building, so every event is counted independently rather than matched into
  stays.

## Data source

[Austin Animal Center Shelter Intakes and Outcomes](https://www.kaggle.com/datasets/aaronschlegel/austin-animal-center-shelter-intakes-and-outcomes)
(public, via Kaggle). Two CSVs of roughly 80,000 rows each, covering intakes and
outcomes through 2018. Dogs and cats make up the large majority of records;
adoption, transfer, and return-to-owner are the dominant outcomes.

## Project structure

```
shelterflow/
├── data/                     # DuckDB file + raw CSVs (gitignored, not committed)
│   ├── bronze/               # aac_intakes.csv, aac_outcomes.csv go here
│   └── shelterflow.duckdb
├── pipelines/
│   └── bronze_ingest.py      # raw CSV → DuckDB bronze tables
├── dbt_shelterflow/          # the dbt project
│   └── models/
│       ├── silver/
│       ├── intermediate/
│       └── gold/
├── notebooks/                # EDA + layer validation
│   ├── eda.ipynb
│   ├── silver_validation.ipynb
│   └── intermediate_validation.ipynb
├── dashboard/
│   └── app.py               # Streamlit app over the gold layer
├── docker/                   # (planned containerization)
└── requirements.txt
```

## Setup

1. Clone the repo.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate     # macOS / Linux
   .venv\Scripts\activate        # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Download the dataset from the Kaggle link above and place
   `aac_intakes.csv` and `aac_outcomes.csv` in `data/bronze/`.

## Running the pipeline

Load the raw CSVs into the DuckDB bronze tables:

```bash
python pipelines/bronze_ingest.py
```

Then build the dbt models (silver → intermediate → gold):

```bash
cd dbt_shelterflow
dbt deps        # install dbt_utils / dbt_expectations
dbt build       # run + test every model in dependency order
```

`dbt build` runs models and their tests together; use `dbt run` and `dbt test`
separately if you want to isolate the two.

For ad-hoc querying, `dbt show --inline` is preferred over the DuckDB CLI, it
resolves `ref()` automatically and handles the schema correctly:

```bash
dbt show --inline "select * from {{ ref('gold_adoption_metrics') }} limit 20"
```

## Dashboard

Once the warehouse is built, launch the Streamlit dashboard from the repo root:

```bash
streamlit run dashboard/app.py
```

The app connects read-only to `data/shelterflow.duckdb` and reads exclusively
from the gold layer, so it is a pure consumer of the modeled tables and never
transforms data itself. It has three tabs, one per gold model:

- **Adoption**: adoption rate by breed for dogs or cats, showing the most and
  least adoptable breeds side by side above an adjustable minimum-stays floor.
- **Long stays**: the distribution and detail of completed stays at or beyond
  the long-stay threshold, filterable by animal type and outcome.
- **Capacity**: monthly intake vs. outcome volume, net flow, and cumulative net
  population over time.

The connection is cached with `@st.cache_resource` and query results with
`@st.cache_data`, so interacting with filters does not re-hit the warehouse on
every rerun. If the gold tables are missing, the app stops with a message
prompting you to build them first rather than raising an error.

## Testing

Data quality is enforced in dbt rather than checked by hand:

- **Schema tests**: `not_null`, `unique`, `accepted_values`, and
  `unique_combination_of_columns` (via dbt_utils) guard grain and domain
  constraints, including the stay grain of `int_animal_stays`.
- **Value-range tests**: dbt_expectations checks bound things like
  non-negative `length_of_stay`, `adoption_rate` in `[0, 1]`, and silver row
  counts within an expected band.
- **A custom singular test**: `assert_capacity_trends_no_month_gaps` fails if
  the monthly capacity series has any gaps, which would let the running total
  step across missing time.

## Documentation

The project ships full dbt docs: model- and column-level descriptions in
`schema.yml`, reusable definitions via `{{ doc() }}` blocks in `docs.md`, source
provenance in `sources.yml`, and a project overview. Generate and browse them
with:

```bash
cd dbt_shelterflow
dbt docs generate
dbt docs serve
```

The `notebooks/` directory holds the exploratory analysis that justified the
cleaning rules (breed standardization, age parsing) and the validation that
confirmed each layer behaves as intended.

## Known limitations

These are documented deliberately rather than silently smoothed over:

- **Same-day sequencing is nondeterministic** for a small number of stays
  (~12 of ~80k), where intake/outcome ordering within a single day can't be
  resolved from the source data.
- **`cumulative_net_population` is relative, not absolute.** It measures change
  since the start of data collection, not the shelter's true headcount, the
  source has no starting census, so read the value as a trend rather than a
  literal count.
- **`breed_standardized` only normalizes cats and dogs.** For other animal
  types the original raw breed value passes through unchanged.

## Roadmap

- **Containerization**: a `docker/` setup for one-command, reproducible runs.
- **Same-day tiebreaker logic**: datetime-based disambiguation for the small
  number of stays where intake/outcome ordering within a single day is currently
  nondeterministic (see [Known limitations](#known-limitations)).