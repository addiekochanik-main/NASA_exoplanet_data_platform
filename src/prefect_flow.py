import subprocess
import sys
from pathlib import Path

from prefect import flow, task

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT = PROJECT_ROOT / "exoplanet_analytics"


@task(name="Ingest NASA data to S3", retries=2, retry_delay_seconds=30)
def ingest_nasa_data():
    subprocess.run(
        [sys.executable, "src/ingest.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )


@task(name="Load S3 data into PostgreSQL", retries=2, retry_delay_seconds=10)
def load_postgres():
    subprocess.run(
        [sys.executable, "src/load_postgres.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )


@task(name="Build and test dbt models", retries=1, retry_delay_seconds=10)
def build_dbt():
    subprocess.run(
        ["dbt", "build"],
        cwd=DBT_PROJECT,
        check=True,
    )


@flow(name="NASA Exoplanet Data Pipeline", log_prints=True)
def nasa_exoplanet_pipeline():
    ingest_nasa_data()
    load_postgres()
    build_dbt()

    print("NASA Exoplanet pipeline completed successfully!")


if __name__ == "__main__":
    nasa_exoplanet_pipeline()
