from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import requests

#pl_name: Planet name most commonly used in the literature 
#hostname: Stellar name most commonly used in the literature
#discoverymethod: Method by which the planet was first identified 
#disc_year: Year the planet was discovered
#pl_rade: Planet Radius: Length of a line segment from the center of the planet to its surface, measured in units of radius of the earth 
#pl_orbper: Orbital Period: Time a planet takes to complete one orbit, measured in days



NASA_API_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

QUERY = """
SELECT
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

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"exoplanets_{timestamp}.csv"
    
    df.to_csv(output_file, index=False)

    print(f"Successfully downloaded {len(df)} exoplanets!")
    print(df.head())
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
