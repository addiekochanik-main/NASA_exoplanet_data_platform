from pathlib import Path

import pandas as pd
import requests


NASA_API_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

QUERY = """
SELECT TOP 100
    pl_name,
    hostname,
    discoverymethod,
    disc_year,
    pl_rade,
    pl_orbper
FROM pscomppars
ORDER BY pl_name
"""


def fetch_exoplanets():
    response = requests.get(
        NASA_API_URL,
        params={
            "query": QUERY,
            "format": "csv",
        },
        timeout=60,
    )

    response.raise_for_status()

    return pd.read_csv(
        __import__("io").StringIO(response.text)
    )


def main():
    df = fetch_exoplanets()

    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "exoplanets_sample.csv"
    df.to_csv(output_file, index=False)

    print(f"Successfully downloaded {len(df)} exoplanets!")
    print(df.head())
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()