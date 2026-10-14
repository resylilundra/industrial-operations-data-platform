import sqlite3

import pandas as pd
import pytest

from backend.load_to_sqlite import _create_tables
from backend.validate_data import (
    validate_energy_data,
    validate_machines,
    validate_production_data,
)


def test_validate_machines_rejects_duplicate_machine_ids():
    raw_df = pd.DataFrame(
        {
            "machine_id": ["M001", "M001"],
            "site_id": ["S001", "S001"],
        }
    )

    valid_df, rejected_df, _ = validate_machines(
        raw_df,
        accepted_site_ids={"S001"},
    )

    print(rejected_df.to_string(index=False))
    assert valid_df.empty
    assert len(rejected_df) == 2
    assert rejected_df["rejection_reason"].str.contains(
        "Duplicate machine_id."
    ).all()


def test_validate_machines_rejects_unknown_site_ids():
    raw_df = pd.DataFrame(
        {
            "machine_id": ["M001", "M002"],
            "site_id": ["S001", "S999"],
        }
    )

    valid_df, rejected_df, _ = validate_machines(
        raw_df,
        accepted_site_ids={"S001"},
    )

    print(rejected_df.to_string(index=False))
    assert valid_df["machine_id"].tolist() == ["M001"]
    assert rejected_df["machine_id"].tolist() == ["M002"]
    assert rejected_df.iloc[0]["rejection_reason"] == (
        "Invalid site_id: not found in accepted sites."
    )


def test_validate_production_data_rejects_negative_output():
    raw_df = pd.DataFrame(
        {
            "timestamp": ["2026-01-01 00:00:00", "2026-01-01 01:00:00"],
            "machine_id": ["M001", "M001"],
            "output_units": [10, -1],
            "defect_units": [1, 0],
            "downtime_minutes": [0, 0],
        }
    )

    valid_df, rejected_df, _ = validate_production_data(
        raw_df,
        accepted_machine_ids={"M001"},
    )

    print(rejected_df.to_string(index=False))
    assert valid_df["output_units"].tolist() == [10]
    assert len(rejected_df) == 1
    assert "output_units cannot be negative." in rejected_df.iloc[0][
        "rejection_reason"
    ]


def test_validate_energy_data_rejects_temperature_above_limit():
    raw_df = pd.DataFrame(
        {
            "timestamp": ["2026-01-01 00:00:00", "2026-01-01 01:00:00"],
            "machine_id": ["M001", "M001"],
            "temperature": [75, 201],
            "energy_kwh": [5, 5],
            "vibration": [0.2, 0.2],
        }
    )

    valid_df, rejected_df, _ = validate_energy_data(
        raw_df,
        accepted_machine_ids={"M001"},
    )

    print(rejected_df.to_string(index=False))
    assert valid_df["temperature"].tolist() == [75]
    assert len(rejected_df) == 1
    assert rejected_df.iloc[0]["rejection_reason"] == (
        "temperature must be between 0 and 200."
    )


def test_sqlite_rejects_machine_with_unknown_site():
    connection = sqlite3.connect(":memory:")
    try:
        _create_tables(connection)

        assert connection.execute("PRAGMA foreign_keys;").fetchone() == (1,)

        with pytest.raises(sqlite3.IntegrityError) as error:
            connection.execute(
                """
                INSERT INTO machines (
                    machine_id,
                    site_id,
                    machine_name,
                    machine_type,
                    department,
                    installation_year,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("M001", "UNKNOWN", "Machine", "Press", "Assembly", 2020, "Active"),
            )

        print(f"SQLite rejected the row: {error.value}")
    finally:
        connection.close()
