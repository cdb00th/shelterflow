"""Load raw Austin Animal Center CSVs into DuckDB bronze tables.

Reads intakes.csv and outcomes.csv from data/ and writes bronze_intakes
and bronze_outcomes. No cleaning as this is the immutable raw layer.
Idempotent: re-running replaces the tables.

"--source full", located in data/bronze/, refers to the complete dataset.
"--source fixture", located tests/fixtures/, refers to the sampled fixture used by CI.
"""
import argparse
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

parser = argparse.ArgumentParser(description="Load AAC CSVs into DuckDB bronze tables.")
parser.add_argument("--source", choices=list(SOURCE_DIRS), required=True)
args = parser.parse_args()
source_dir = SOURCE_DIRS[args.source]

DATA_DIR.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DATA_DIR / "shelterflow.duckdb"))

intakes = pd.read_csv(source_dir / "aac_intakes.csv", dtype=str)
outcomes = pd.read_csv(source_dir / "aac_outcomes.csv", dtype=str)

# OR REPLACE so re-running the script reloads cleanly instead of erroring
con.execute("CREATE OR REPLACE TABLE bronze_intakes AS SELECT * FROM intakes")
con.execute("CREATE OR REPLACE TABLE bronze_outcomes AS SELECT * FROM outcomes")

con.close()
