import pandas as pd
import duckdb

con = duckdb.connect("../data/shelterflow.duckdb")

# Load CSVs into Pandas DataFrames
intakes = pd.read_csv("../data/bronze/aac_intakes.csv")
outcomes = pd.read_csv("../data/bronze/aac_outcomes.csv")

# Create (or replace existing) DuckDB tables from Pandas DataFrames
con.execute("CREATE OR REPLACE TABLE bronze_intakes AS SELECT * FROM intakes")
con.execute("CREATE OR REPLACE TABLE bronze_outcomes AS SELECT * FROM outcomes")

con.close()
