
import csv
import io
import os

import boto3
import psycopg

AWS_PROFILE = "nasa-exoplanet"
S3_BUCKET = "nasa-exoplanet-data-platform"
S3_PREFIX = "raw/"
DB_NAME = "nasa_exoplanets"


def main():
    session = boto3.Session(profile_name=AWS_PROFILE)
    s3 = session.client("s3")

    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)

    files = [
        obj for obj in response.get("Contents", [])
        if obj["Key"].endswith(".csv")
    ]

    if not files:
        raise RuntimeError("No CSV snapshots found in S3.")

    latest = max(files, key=lambda obj: obj["LastModified"])
    key = latest["Key"]

    print(f"Loading s3://{S3_BUCKET}/{key}")

    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    csv_text = obj["Body"].read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(csv_text))
    columns = [
        "pl_name",
        "hostname",
        "discoverymethod",
        "disc_year",
        "pl_rade",
        "pl_orbper",
    ]

    with psycopg.connect(
        dbname=DB_NAME,
        user=os.environ.get("USER"),
        host="localhost",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.raw_exoplanets (
                    pl_name TEXT,
                    hostname TEXT,
                    discoverymethod TEXT,
                    disc_year INTEGER,
                    pl_rade DOUBLE PRECISION,
                    pl_orbper DOUBLE PRECISION
                )
            """)

            cur.execute("TRUNCATE TABLE public.raw_exoplanets")

            with cur.copy("""
                COPY public.raw_exoplanets
                (pl_name, hostname, discoverymethod, disc_year, pl_rade, pl_orbper)
                FROM STDIN
            """) as copy:
                count = 0

                for row in reader:
                    copy.write_row([
                        row[col] if row[col] not in ("", None) else None
                        for col in columns
                    ])
                    count += 1

    print(f"Successfully loaded {count:,} exoplanets into PostgreSQL.")


if __name__ == "__main__":
    main()
