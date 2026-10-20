import pandas as pd

from backend import prefect_pipeline
from backend.query_parquet import get_total_output


def test_reprocessing_batch_is_skipped_and_new_batch_is_processed(
    tmp_path,
    monkeypatch,
):
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    pd.DataFrame({"machine_id": ["M001"]}).to_csv(
        processed_dir / "machines_clean.csv",
        index=False,
    )

    batches = {
        "raw/production/production_batch-one.csv": pd.DataFrame(
            [
                {
                    "timestamp": "2026-10-17 22:00:00",
                    "machine_id": "M001",
                    "output_units": 100,
                    "defect_units": 2,
                    "downtime_minutes": 0,
                }
            ]
        ),
        "raw/production/production_batch-two.csv": pd.DataFrame(
            [
                {
                    "timestamp": "2026-10-17 22:00:10",
                    "machine_id": "M001",
                    "output_units": 50,
                    "defect_units": 1,
                    "downtime_minutes": 0,
                }
            ]
        ),
    }
    monkeypatch.setattr(
        prefect_pipeline,
        "read_production_batch",
        lambda object_key: batches[object_key],
    )

    first_key = "raw/production/production_batch-one.csv"
    assert prefect_pipeline.process_batch.fn(
        "production",
        first_key,
        "etag-one",
        tmp_path,
    )
    parquet_glob = str(
        tmp_path
        / "data_lake"
        / "processed"
        / "production"
        / "**"
        / "*.parquet"
    )
    assert get_total_output(parquet_glob) == 100

    assert not prefect_pipeline.process_batch.fn(
        "production",
        first_key,
        "etag-one",
        tmp_path,
    )
    assert get_total_output(parquet_glob) == 100

    assert prefect_pipeline.process_batch.fn(
        "production",
        "raw/production/production_batch-two.csv",
        "etag-two",
        tmp_path,
    )
    assert get_total_output(parquet_glob) == 150
