import os
from pathlib import Path

import boto3
import pandas as pd

from backend.validate_data import (
    validate_energy_data,
    validate_production_data,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUCKET_NAME = "industrial-operations"

def read_production_batch(object_key):
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
        region_name="us-east-1",
    )

    result = client.get_object(Bucket=BUCKET_NAME, Key=object_key)
    return pd.read_csv(result["Body"])

def read_energy_batch(object_key):
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
        region_name="us-east-1",
    )

    result = client.get_object(Bucket=BUCKET_NAME, Key=object_key)
    return pd.read_csv(result["Body"])

def process_production_batch(raw_df, batch_id, project_root=PROJECT_ROOT):
    machines_path = project_root / "data" / "processed" / "machines_clean.csv"
    accepted_machine_ids = set(
        pd.read_csv(machines_path)["machine_id"].astype(str).str.upper()
    )

    valid_df, rejected_df, corrections = validate_production_data(
        raw_df,
        accepted_machine_ids,
    )

    processed_base = (
        project_root / "data_lake" / "processed" / "production"
    )
    rejected_dir = project_root / "data_lake" / "rejected" / "production"
    output_paths = []

    if not valid_df.empty:
        valid_df = valid_df.copy()
        valid_df["timestamp"] = pd.to_datetime(valid_df["timestamp"])

        for date, daily_df in valid_df.groupby(valid_df["timestamp"].dt.date):
            output_dir = (
                processed_base
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            parquet_path = output_dir / f"production_{batch_id}.parquet"
            daily_df.to_parquet(parquet_path, index=False)
            output_paths.append(parquet_path)

    if not rejected_df.empty:
        rejected_dir.mkdir(parents=True, exist_ok=True)
        rejected_path = rejected_dir / f"production_rejected_{batch_id}.csv"
        rejected_df.to_csv(rejected_path, index=False)
        output_paths.append(rejected_path)

    return output_paths, corrections

def process_energy_batch(raw_df, batch_id, project_root=PROJECT_ROOT):
    machines_path = project_root / "data" / "processed" / "machines_clean.csv"
    accepted_machine_ids = set(
        pd.read_csv(machines_path)["machine_id"].astype(str).str.upper()
    )

    valid_df, rejected_df, corrections = validate_energy_data(
        raw_df,
        accepted_machine_ids,
    )

    processed_base = project_root / "data_lake" / "processed" / "energy"
    rejected_dir = project_root / "data_lake" / "rejected" / "energy"
    output_paths = []

    if not valid_df.empty:
        valid_df = valid_df.copy()
        valid_df["timestamp"] = pd.to_datetime(valid_df["timestamp"])

        for date, daily_df in valid_df.groupby(valid_df["timestamp"].dt.date):
            output_dir = (
                processed_base
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            parquet_path = output_dir / f"energy_{batch_id}.parquet"
            daily_df.to_parquet(parquet_path, index=False)
            output_paths.append(parquet_path)

    if not rejected_df.empty:
        rejected_dir.mkdir(parents=True, exist_ok=True)
        rejected_path = rejected_dir / f"energy_rejected_{batch_id}.csv"
        rejected_df.to_csv(rejected_path, index=False)
        output_paths.append(rejected_path)

    return output_paths, corrections

if __name__ == "__main__":
    object_key = "raw/production/production_20261017T224156Z.csv"
    raw_df = read_production_batch(object_key)

    output_paths, corrections = process_production_batch(
        raw_df,
        "20261017T224156Z",
    )

    print("Created output files:")
    for path in output_paths:
        print(path)

    if corrections:
        print("Corrections:")
        for correction in corrections:
            print(correction)
