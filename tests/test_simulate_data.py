import pandas as pd

from backend.simulate_data import write_batch_files


def test_write_batch_files_creates_csv_files(tmp_path):
    production_records = [
        {
            "timestamp": "2026-10-17 22:00:00",
            "machine_id": "M001",
            "output_units": 100,
            "defect_units": 2,
            "downtime_minutes": 5,
        }
    ]
    energy_records = [
        {
            "timestamp": "2026-10-17 22:00:00",
            "machine_id": "M001",
            "temperature": 75,
            "energy_kwh": 12,
            "vibration": 0.2,
        }
    ]

    production_path, energy_path = write_batch_files(
        production_records,
        energy_records,
        "20261017T220000Z",
        tmp_path,
    )

    assert production_path.exists()
    assert energy_path.exists()

    production_df = pd.read_csv(production_path)
    energy_df = pd.read_csv(energy_path)

    assert production_df.columns.tolist() == [
        "timestamp",
        "machine_id",
        "output_units",
        "defect_units",
        "downtime_minutes",
    ]
    assert len(production_df) == 1
    assert production_df.iloc[0]["output_units"] == 100

    assert energy_df.columns.tolist() == [
        "timestamp",
        "machine_id",
        "temperature",
        "energy_kwh",
        "vibration",
    ]
    assert len(energy_df) == 1
    assert energy_df.iloc[0]["temperature"] == 75
