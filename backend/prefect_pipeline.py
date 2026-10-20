import os
from pathlib import Path

import boto3
from prefect import flow, task

from backend.batch_state import is_batch_processed, mark_batch_processed
from backend.process_raw_batch import (
    BUCKET_NAME,
    process_energy_batch,
    process_production_batch,
    read_energy_batch,
    read_production_batch,
)


def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
        region_name="us-east-1",
    )


@task
def discover_raw_batches(data_type: str) -> list[tuple[str, str]]:
    prefix = f"raw/{data_type}/"
    paginator = get_minio_client().get_paginator("list_objects_v2")
    objects = []

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            relative_key = key[len(prefix):]

            # Only pick CSVs directly inside raw/production or raw/energy.
            if "/" not in relative_key and key.endswith(".csv"):
                etag = item["ETag"].strip('"')
                objects.append((key, etag))

    print(f"Found {len(objects)} {data_type} CSV file(s).")
    return objects


@task
def process_batch(
    data_type: str,
    object_key: str,
    etag: str,
    project_root: Path = Path(__file__).resolve().parent.parent,
) -> bool:
    if is_batch_processed(data_type, object_key, etag, project_root):
        print(f"Skipping already processed batch: {object_key}")
        return False

    batch_id = Path(object_key).stem.removeprefix(f"{data_type}_")

    if data_type == "production":
        raw_df = read_production_batch(object_key)
        output_paths, corrections = process_production_batch(
            raw_df,
            batch_id,
            project_root=project_root,
        )
    elif data_type == "energy":
        raw_df = read_energy_batch(object_key)
        output_paths, corrections = process_energy_batch(
            raw_df,
            batch_id,
            project_root=project_root,
        )
    else:
        raise ValueError(f"Unsupported data type: {data_type}")

    mark_batch_processed(data_type, object_key, etag, project_root)
    print(f"Processed {object_key}")
    for path in output_paths:
        print(f"Created: {path}")
    for correction in corrections:
        print(f"Correction: {correction}")
    return True


@flow(name="industrial-operations-data-pipeline")
def run_data_lake_pipeline() -> None:
    for data_type in ("production", "energy"):
        for object_key, etag in discover_raw_batches(data_type):
            process_batch(data_type, object_key, etag)

if __name__ == "__main__":
    run_data_lake_pipeline.serve(
        name="industrial-operations-hourly",
        cron="0 * * * *",
    )