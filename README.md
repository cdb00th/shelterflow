# ShelterFlow

An analytics engineering project that models the flow of animals through the
Austin Animal Center (arrivals, length of stay, and outcomes) using a dbt +
DuckDB + S3 medallion pipeline. It turns two raw, messy public CSVs into tested,
documented, analytics-ready tables for adoption, long-stay, and shelter-capacity
analysis.

This repository is complete end to end, and runs two ways. The `dev` target
builds entirely from local CSVs into a single DuckDB file, so the project
clones and runs with no cloud account and no credentials. The `prod` target
reads bronze from S3 and publishes the gold models back as parquet, driven by
a GitHub Actions workflow that assumes an AWS role through OIDC rather than
storing access keys. Tests, documentation, and a Streamlit dashboard over the
gold layer are in place throughout.

## Why this project

Animal shelters generate exactly the kind of operational event data that rewards
careful modeling: the same animal can appear many times, "intake" and "outcome"
are separate event streams that have to be matched into stays, and naive joins
silently fan out. ShelterFlow treats those problems as the point; every
non-obvious modeling decision is documented in-code and tested rather than
hand-waved.

## Tech stack

| Layer | Tool |
|-------|------|
| Transformation | dbt Core 1.11.11 |
| Warehouse / engine | DuckDB (file-based, `data/shelterflow.duckdb`) |
| Adapter | dbt-duckdb 1.10.1 |
| Testing packages | dbt_utils, dbt_expectations |
| CI | GitHub Actions |
| Dashboard | Streamlit, Altair |
| Ingestion / EDA | Python (pandas, duckdb), Jupyter |
| Object storage | AWS S3 (via DuckDB httpfs) |

Using DuckDB keeps the whole warehouse in a single file, so the project clones
and runs with no external database to provision.

## Architecture

ShelterFlow follows a medallion layout. Each layer has a single, well-scoped
responsibility:

- **bronze**: raw Austin Animal Center intake and outcome records, loaded
  as-is by `pipelines/bronze_ingest.py` from either local CSVs or parquet in
  S3. No cleaning; this is the immutable source of truth.
- **silver**: `silver_intakes` and `silver_outcomes`. Deduplicated, typed, and
  standardized: breed strings collapsed to canonical names (for cats and dogs),
  ages parsed from free text into `age_in_days`, life-stage `age_group` buckets
  derived, and datetimes normalized to dates.
- **intermediate**: `int_animal_stays`. Pairs each intake to its next outcome
  on or after the intake date, producing one row per completed stay. Handles
  repeat visitors and resolves a join fan-out that would otherwise let two
  same-day intakes both claim a single outcome.
- **gold**: analytics-ready models the dashboard and any downstream consumer
  read from. The Streamlit dashboard reads exclusively from this layer. On the
  `prod` target these materialize as external parquet in S3 instead of tables
  in the local file, so the published artifacts are readable without the
  warehouse that produced them.

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
  cumulative net-change running total. Reads the silver layer directly rather
  than `int_animal_stays`, because capacity is about physical movement through
  the building, so every event is counted independently rather than matched into
  stays.

## Data source

[Austin Animal Center Shelter Intakes and Outcomes](https://www.kaggle.com/datasets/aaronschlegel/austin-animal-center-shelter-intakes-and-outcomes)
(public, via Kaggle). Two CSVs of roughly 80,000 rows each, covering intakes and
outcomes through 2018 across 72,365 distinct animals. Dogs and cats make up the
large majority of records; adoption, transfer, and return-to-owner are the
dominant outcomes.

## Project structure

```
shelterflow/
├── .github/
│   └── workflows/
│       ├── ci.yml            # build + test the full DAG on every push
│       └── prod.yml          # manual full-dataset build against S3
├── data/                     # DuckDB file + raw CSVs (gitignored, not committed)
│   ├── bronze/               # aac_intakes.csv, aac_outcomes.csv go here
│   └── shelterflow.duckdb
├── pipelines/
│   └── bronze_ingest.py      # raw CSV or S3 parquet → DuckDB bronze tables
├── scripts/
│   └── build_fixture.py      # generates the sampled CI fixture
├── tests/
│   └── fixtures/             # sampled CSVs used by CI (committed)
├── dbt_shelterflow/          # the dbt project
│   ├── profiles.yml          # dev and prod targets
│   └── models/
│       ├── silver/
│       ├── intermediate/
│       └── gold/
├── notebooks/                # EDA + layer validation
│   ├── eda.ipynb
│   ├── silver_validation.ipynb
│   └── intermediate_validation.ipynb
├── dashboard/
│   └── app.py                # Streamlit app over the gold layer
└── requirements.txt
```

## Setup
Python 3.12 is required.

1. Clone the repo.
2. Create and activate a virtual environment:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate     # macOS / Linux
   .venv\Scripts\activate        # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Download the dataset from the Kaggle link above and place
   `aac_intakes.csv` and `aac_outcomes.csv` in `data/bronze/`.

Steps 1–4 are everything needed to run the project. The `prod` target
additionally requires a configured AWS CLI and `SHELTERFLOW_BUCKET` set to an
S3 bucket you own:

```bash
export SHELTERFLOW_BUCKET=your-bucket-name
```

Neither is needed for `dev`. The profile supplies an empty default for
`SHELTERFLOW_BUCKET`, so the project parses and builds on a machine with no AWS
configuration at all.

## Running the pipeline

Load the raw CSVs into the DuckDB bronze tables:

```bash
python pipelines/bronze_ingest.py --source full
```

`--source` is required and selects which data to load:

- `full` — the complete dataset, from local CSVs in `data/bronze/`
- `fixture` — the sampled CI fixture, from local CSVs in `tests/fixtures/`
- `s3` — the complete dataset, as parquet from S3 over DuckDB's httpfs

There is no default, so every invocation is explicit about which data it built.
All three write to the same bronze tables in the same database file, which means
loading the fixture locally overwrites a full build; re-run with `--source full`
to restore.

Then build the dbt models (silver → intermediate → gold):

```bash
cd dbt_shelterflow
dbt deps        # install dbt_utils / dbt_expectations
dbt build       # run + test every model in dependency order
```

`dbt build` runs models and their tests together; use `dbt run` and `dbt test`
separately if you want to isolate the two.

For ad-hoc querying, `dbt show --inline` is preferred over the DuckDB CLI, since
it resolves `ref()` automatically and handles the schema correctly:

```bash
dbt show --inline "select * from {{ ref('gold_adoption_metrics') }} limit 20"
```

### Building against S3

The `prod` target reads bronze from S3 and writes the gold models back as
parquet:

```bash
python pipelines/bronze_ingest.py --source s3
cd dbt_shelterflow
dbt build --target prod
```

Silver and intermediate stay in the local DuckDB file. They are intermediate
state rather than artifacts, so pushing them to object storage would add round
trips without giving any consumer something to read.

Credentials are resolved by DuckDB's `credential_chain` provider, which reads
the same `~/.aws/credentials` the AWS CLI uses. No credentials appear in the
profile or anywhere else in the repository.

## Continuous integration

[![CI](https://github.com/cdb00th/shelterflow/actions/workflows/ci.yml/badge.svg)](https://github.com/cdb00th/shelterflow/actions/workflows/ci.yml)

Every push and pull request to `main` runs the pipeline end to end on GitHub
Actions: install dependencies, load a fixture into DuckDB, and `dbt build` the
entire DAG with its tests.

CI runs against a committed fixture in `tests/fixtures/` rather than the full
dataset, which is not in the repo. Keeping the build hermetic means a red badge
means the code broke, not that an upstream host was slow.

The fixture covers 3,000 animals and is generated by `scripts/build_fixture.py`.
All 98 animals with a `Black/Tan` breed are force-included, since at 0.14% of the
population a uniform draw would likely miss them entirely and leave the breed-
standardization path untested. The rest is a seeded reservoir draw. Every intake
and outcome row for a sampled animal is pulled, so stay histories arrive intact
for `int_animal_stays` to pair.

The fixture is deliberately **not** representative, and statistics computed from
it will not match the full dataset. The row-count tests that assert full-dataset
volume are tagged `full_data` and excluded in CI rather than widened to
accommodate the sample: a bound loose enough to pass on 3,000 rows and 80,000
rows is not checking anything.

Regenerate the fixture (requires a full local build first):

```bash
python scripts/build_fixture.py
```

### Production builds

A second workflow, `prod.yml`, runs the pipeline against the full dataset in
S3: bronze parquet in, gold parquet back out. It is triggered manually rather
than on a schedule, since the AAC extract is a static snapshot and a nightly
run would republish byte-identical files.

It authenticates to AWS through GitHub's OIDC provider, assuming an IAM role
via `AssumeRoleWithWebIdentity` rather than reading stored access keys. No
long-lived AWS credentials exist in the repository or its secrets; the token is
issued per run and expires with the job. The role's trust policy scopes the
`sub` claim to this repository, so a workflow in any other repository
presenting a valid GitHub token still cannot assume it, and its S3 policy is
limited to the single project bucket.

The two workflows are deliberately separate. `ci.yml` runs on every push and
pull request and never touches AWS, so build status keeps meaning "the code
broke." `prod.yml` is the only place credentials, network access, and the full
dataset are involved, and it runs when the published artifacts need refreshing.

## Dashboard

Once the warehouse is built, launch the Streamlit dashboard from the repo root:

```bash
streamlit run dashboard/app.py
```

The app connects read-only to `data/shelterflow.duckdb` and reads exclusively
from the gold layer, so it is a pure consumer of the modeled tables and never
transforms data itself. It has three tabs, one per gold model:

- **Adoption**: adoption rate by breed for dogs or cats, showing the most and
  least adoptable breeds side by side. Breeds are held to a fixed reliability
  floor of 50 completed stays, with an adjustable control for how many to show
  at each end.
- **Long stays**: the distribution and detail of completed stays at or beyond
  the long-stay threshold, filterable by animal type and outcome.
- **Capacity**: monthly intake vs. outcome volume, net flow, and cumulative net
  change over time.

The connection is cached with `@st.cache_resource` and query results with
`@st.cache_data`, so interacting with filters does not re-hit the warehouse on
every rerun. If the gold tables are missing, the app stops with a message
prompting you to build them first rather than raising an error.

## Testing

Data quality is enforced in dbt rather than checked by hand. There are 28 tests
in total; 26 run in CI, the two exclusions being the full-dataset row-count
bounds described below.

- **Schema tests**: `not_null`, `unique`, `accepted_values`, and
  `unique_combination_of_columns` (via dbt_utils) guard grain and domain
  constraints, including the stay grain of `int_animal_stays`.
- **Value-range tests**: dbt_expectations checks bound things like
  non-negative `length_of_stay` and `adoption_rate` in `[0, 1]`.
- **Load-completeness tests**: silver row counts are asserted to fall within an
  expected band. These check that the full dataset loaded without truncation, so
  they are tagged `full_data` and excluded when CI runs against the fixture.
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

## Notes on the data

- **December adoptions run above adjacent months in every year of the data.**
  Measured against the mean of the neighboring November and January, December
  adoptions are higher in all five year-pairs, ranging from +4% to +28%. The
  effect is strongest in 2013–14 and diminishes in later years, where December
  adoptions take a larger share of outcomes without adding overall volume.

## Known limitations

These are documented deliberately rather than silently smoothed over:

- **Same-day sequencing is nondeterministic** for a small number of stays
  (~12 of ~80k), where intake/outcome ordering within a single day can't be
  resolved from the source data.
- **`cumulative_net_change` is relative, not absolute.** The running sum starts
  at zero in the first month of the extract, which assumes an empty shelter at
  that point. Animals already in residence produce outcomes with no matching
  intake, so the series measures net change since data collection began rather
  than the shelter's headcount. Read it as a trend, not a count.
- **`breed_standardized` only normalizes cats and dogs.** For other animal
  types the original raw breed value passes through unchanged.

## Roadmap

- **Same-day tiebreaker logic**: datetime-based disambiguation for the small
  number of stays where intake/outcome ordering within a single day is currently
  nondeterministic (see [Known limitations](#known-limitations)).