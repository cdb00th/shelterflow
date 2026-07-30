"""Generate a sampled fixture from the full AAC dataset for CI.

The sample is deliberately not representative: all 98 animals with a
Black/Tan breed are force-included so that
CI exercises the breed-standardization path. Do not compute statistics
from it.

Run locally, commit the output CSVs. Requires a full local build.
"""
from pathlib import Path
import duckdb

DB_PATH = "data/shelterflow.duckdb"              
OUT_INTAKES = "tests/fixtures/aac_intakes.csv"          
OUT_OUTCOMES = "tests/fixtures/aac_outcomes.csv"
TARGET_ANIMALS = 3000
SEED = 42


def select_animal_ids(con) -> list[str]:
    """Force-include Black/Tan animals, random-fill to TARGET_ANIMALS."""
    forced = [row[0] for row in con.execute("""
        SELECT DISTINCT animal_id
        FROM bronze_intakes
        WHERE breed LIKE '%Black/Tan%'
    """).fetchall()]

    n_fill = TARGET_ANIMALS - len(forced)

    fill = [row[0] for row in con.execute(f"""
        SELECT animal_id FROM (
            SELECT DISTINCT animal_id
            FROM bronze_intakes
            WHERE breed NOT LIKE '%Black/Tan%'
        ) USING SAMPLE reservoir({n_fill} ROWS) REPEATABLE ({SEED})
    """).fetchall()]

    return forced + fill


def export(con, ids: list[str]) -> None:
    """Write all intake and outcome rows for `ids` to CSV."""
    Path(OUT_INTAKES).parent.mkdir(parents=True, exist_ok=True)

    id_list = ", ".join(f"'{animal_id}'" for animal_id in ids)

    for table, out_path in [
        ("bronze_intakes", OUT_INTAKES),
        ("bronze_outcomes", OUT_OUTCOMES),
    ]:
        con.execute(f"""
            COPY (
                SELECT * FROM {table}
                WHERE animal_id IN ({id_list})
                ORDER BY animal_id, datetime
            ) TO '{out_path}' (HEADER)
        """)   


def verify(con, ids: list[str]) -> None:
    """Assert the fixture is the right size, covers Black/Tan, and has no month gaps."""
    assert len(ids) == TARGET_ANIMALS, f"got {len(ids)} ids, want {TARGET_ANIMALS}"

    missing = con.execute(f"""
        SELECT count(*) FROM (
            SELECT DISTINCT animal_id FROM bronze_intakes
            WHERE breed LIKE '%Black/Tan%'
            EXCEPT
            SELECT DISTINCT animal_id
            FROM read_csv('{OUT_INTAKES}', all_varchar=true)
        )
    """).fetchone()[0]
    assert missing == 0, f"{missing} Black/Tan animals missing from fixture"

    for out_path in (OUT_INTAKES, OUT_OUTCOMES):
        present, expected = con.execute(f"""
            SELECT
                count(DISTINCT date_trunc('month', CAST(datetime AS TIMESTAMP))),
                datediff('month', min(CAST(datetime AS TIMESTAMP)),
                                  max(CAST(datetime AS TIMESTAMP))) + 1
            FROM read_csv('{out_path}', all_varchar=true)
        """).fetchone()
        assert present == expected, f"{out_path}: {present} months present, {expected} expected"


def main() -> None:
    con = duckdb.connect(DB_PATH, read_only=True)
    ids = select_animal_ids(con)
    export(con, ids)
    verify(con, ids)


if __name__ == "__main__":
    main()