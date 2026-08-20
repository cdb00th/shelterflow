"""Load raw Austin Animal Center data into DuckDB bronze tables.

Reads intakes.csv and outcomes.csv from data/ and writes bronze_intakes
and bronze_outcomes. No cleaning as this is the immutable raw layer.
Idempotent: re-running replaces the tables. Both --source values write to the
same database, so loading the fixture locally overwrites a full build.
Re-run with --source full to restore.

"--source full", located in data/bronze/, refers to the complete dataset.
"--source fixture", located tests/fixtures/, refers to the sampled fixture used by CI.
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import duckdb

# Anchor all paths to the project root (one level up from this script),
# so the script runs the same from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

SOURCE_DIRS = {
    "full": DATA_DIR / "bronze",
    "fixture": PROJECT_ROOT / "tests" / "fixtures",
}

parser = argparse.ArgumentParser(description="Load AAC raw data into DuckDB bronze tables.")
parser.add_argument("--source", choices=[*SOURCE_DIRS, "s3"], required=True)
args = parser.parse_args()

DATA_DIR.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DATA_DIR / "shelterflow.duckdb"))

if args.source == "s3":
    bucket = os.environ["SHELTERFLOW_BUCKET"]

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("CREATE SECRET (TYPE s3, PROVIDER credential_chain, REGION 'us-east-1')")

    intakes_source = f"read_parquet('s3://{bucket}/bronze/aac_intakes.parquet')"
    outcomes_source = f"read_parquet('s3://{bucket}/bronze/aac_outcomes.parquet')"
else:
    source_dir = SOURCE_DIRS[args.source]

    intakes = pd.read_csv(source_dir / "aac_intakes.csv", dtype=str)
    outcomes = pd.read_csv(source_dir / "aac_outcomes.csv", dtype=str)
    intakes_source = "intakes"
    outcomes_source = "outcomes"

# OR REPLACE so re-running the script reloads cleanly instead of erroring
con.execute(f"CREATE OR REPLACE TABLE bronze_intakes AS SELECT * FROM {intakes_source}")
con.execute(f"CREATE OR REPLACE TABLE bronze_outcomes AS SELECT * FROM {outcomes_source}")

con.close()
