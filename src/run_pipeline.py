
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT = PROJECT_ROOT / "exoplanet_analytics"


def run_step(name, command, cwd=PROJECT_ROOT):
    print(f"\n{'=' * 50}", flush=True)
    print(f"Starting: {name}", flush=True)
    print(f"{'=' * 50}", flush=True)

    subprocess.run(
        command,
        cwd=cwd,
        check=True,
    )

    print(f"Completed: {name}", flush=True)


def main():
    run_step(
        "NASA API ingestion to S3",
        [sys.executable, "src/ingest.py"],
    )

    run_step(
        "S3 to PostgreSQL loading",
        [sys.executable, "src/load_postgres.py"],
    )

    run_step(
        "dbt transformations and tests",
        ["dbt", "build"],
        cwd=DBT_PROJECT,
    )

    print("\nPipeline completed successfully!")


if __name__ == "__main__":
    main()
