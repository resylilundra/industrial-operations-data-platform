import pandas as pd

from backend.process_raw_batch import process_production_batch


def test_process_production_batch_writes_parquet_and_rejections(tmp_path):
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    pd.DataFrame({"machine_id": ["M001"]}).to_csv(
        processed_dir / "machines_clean.csv",
        index=False,
    )

    raw_df = pd.DataFrame(
        [
            {
                "timestamp": "2026-10-17 22:00:00",
                "machine_id": "M001",
                "output_units": 100,
                "defect_units": 2,
                "downtime_minutes": 0,
            },
            {
                "timestamp": "2026-10-17 22:00:10",
                "machine_id": "M001",
                "output_units": -1,
                "defect_units": 0,
                "downtime_minutes": 0,
            },
        ]
    )

    output_paths, _ = process_production_batch(
        raw_df,
        "test-batch",
        project_root=tmp_path,
    )

    parquet_path = next(path for path in output_paths if path.suffix == ".parquet")
    rejected_path = next(path for path in output_paths if path.suffix == ".csv")

    valid_df = pd.read_parquet(parquet_path)
    rejected_df = pd.read_csv(rejected_path)

    assert len(valid_df) == 1
    assert valid_df.iloc[0]["machine_id"] == "M001"
    assert valid_df.iloc[0]["output_units"] == 100

    assert len(rejected_df) == 1
    assert rejected_df.iloc[0]["output_units"] == -1
    assert "rejection_reason" in rejected_df.columns
    assert "output_units cannot be negative." in rejected_df.iloc[0][
        "rejection_reason"
    ]

