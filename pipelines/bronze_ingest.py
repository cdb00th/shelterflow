"""Load raw Austin Animal Center CSVs into DuckDB bronze tables.

Reads intakes.csv and outcomes.csv from data/ and writes bronze_intakes
and bronze_outcomes. No cleaning as this is the immutable raw layer.
Idempotent: re-running replaces the tables.
"""

import pandas as pd
import duckdb

con = duckdb.connect("../data/shelterflow.duckdb")

intakes = pd.read_csv("../data/bronze/aac_intakes.csv")
outcomes = pd.read_csv("../data/bronze/aac_outcomes.csv")

# OR REPLACE so re-running the script reloads cleanly instead of erroring
con.execute("CREATE OR REPLACE TABLE bronze_intakes AS SELECT * FROM intakes")
con.execute("CREATE OR REPLACE TABLE bronze_outcomes AS SELECT * FROM outcomes")

con.close()
