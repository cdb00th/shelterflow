"""Load raw Austin Animal Center CSVs into DuckDB bronze tables.

Reads intakes.csv and outcomes.csv from data/ and writes bronze_intakes
and bronze_outcomes. No cleaning as this is the immutable raw layer.
Idempotent: re-running replaces the tables.
"""
from pathlib import Path

import pandas as pd
import duckdb

# Anchor all paths to the project root (one level up from this script),
# so the script runs the same from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"

con = duckdb.connect(str(DATA_DIR / "shelterflow.duckdb"))

intakes = pd.read_csv(BRONZE_DIR / "aac_intakes.csv")
outcomes = pd.read_csv(BRONZE_DIR / "aac_outcomes.csv")

# OR REPLACE so re-running the script reloads cleanly instead of erroring
con.execute("CREATE OR REPLACE TABLE bronze_intakes AS SELECT * FROM intakes")
con.execute("CREATE OR REPLACE TABLE bronze_outcomes AS SELECT * FROM outcomes")

con.close()
