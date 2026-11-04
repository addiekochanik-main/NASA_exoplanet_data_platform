
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "dashboard" / "data"
DBT_RESULTS = (
    PROJECT_ROOT
    / "exoplanet_analytics"
    / "target"
    / "run_results.json"
)

QUERIES = {
    "yearly": """
        SELECT *
        FROM analytics.discoveries_by_year
        ORDER BY disc_year
    """,
    "methods": """
        SELECT *
        FROM analytics.discoveries_by_method
        ORDER BY total_planets DESC
    """,
    "characteristics": """
        SELECT *
        FROM analytics.planet_characteristics
        ORDER BY total_planets DESC
    """,
    "planets": """
        SELECT
            pl_name,
            hostname,
            discoverymethod,
            disc_year,
            pl_rade,
            pl_orbper
        FROM public.raw_exoplanets
    """,
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(
        dbname="nasa_exoplanets",
        user=os.environ.get("USER"),
        host="localhost",
    ) as conn:
        for name, query in QUERIES.items():
            with conn.cursor() as cur:
                cur.execute(query)
                columns = [col.name for col in cur.description]
                rows = cur.fetchall()

            df = pd.DataFrame(rows, columns=columns)
            output_path = OUTPUT_DIR / f"{name}.csv"
            df.to_csv(output_path, index=False)

            print(f"Exported {len(df):,} rows to {output_path}")

    metadata = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "dbt_tests": None,
    }

    if DBT_RESULTS.exists():
        with DBT_RESULTS.open("r", encoding="utf-8") as file:
            results = json.load(file)

        tests = [
            result
            for result in results.get("results", [])
            if result.get("unique_id", "").startswith("test.")
        ]

        if tests:
            metadata["dbt_tests"] = {
                "passed": sum(
                    result.get("status") == "pass"
                    for result in tests
                ),
                "total": len(tests),
                "generated_at": results.get(
                    "metadata", {}
                ).get("generated_at"),
            }

    metadata_path = OUTPUT_DIR / "metadata.json"

    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"Exported metadata to {metadata_path}")
    print("Dashboard export complete!")


if __name__ == "__main__":
    main()
