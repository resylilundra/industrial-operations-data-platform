import pandas as pd

from backend.process_raw_batch import process_energy_batch


def test_process_energy_batch_writes_parquet_and_rejections(tmp_path):
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
                "temperature": 75,
                "energy_kwh": 12,
                "vibration": 0.2,
            },
            {
                "timestamp": "2026-10-17 22:00:10",
                "machine_id": "M001",
                "temperature": 201,
                "energy_kwh": 12,
                "vibration": 0.2,
            },
        ]
    )

    output_paths, _ = process_energy_batch(
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
    assert valid_df.iloc[0]["temperature"] == 75

    assert len(rejected_df) == 1
    assert rejected_df.iloc[0]["temperature"] == 201
    assert "rejection_reason" in rejected_df.columns
    assert "temperature must be between 0 and 200." in rejected_df.iloc[0][
     
   "rejection_reason"
    ]
