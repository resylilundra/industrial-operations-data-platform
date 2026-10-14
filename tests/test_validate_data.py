import sqlite3

import pandas as pd
import pytest

from backend.load_to_sqlite import _create_tables, load_data
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
def test_create_tables_keeps_existing_production_readings():
    connection = sqlite3.connect(":memory:")

    try:
        _create_tables(connection)

        connection.execute(
            """
            INSERT INTO sites (site_id, site_name, country, city, site_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("S001", "Example Site", "USA", "Chicago", "Factory"),
        )
        connection.execute(
            """
            INSERT INTO machines (
                machine_id, site_id, machine_name, machine_type,
                department, installation_year, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("M001", "S001", "Example Machine", "Press", "Assembly", 2020, "Active"),
        )
        connection.execute(
            """
            INSERT INTO production_data (
                timestamp, machine_id, output_units, defect_units, downtime_minutes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-01-01 08:00:00", "M001", 100, 2, 5),
        )
        connection.commit()

        _create_tables(connection)

        reading_count = connection.execute(
            "SELECT COUNT(*) FROM production_data"
        ).fetchone()[0]

        assert reading_count == 1
    finally:
        connection.close()


def test_load_data_skips_duplicate_csv_rows_and_preserves_simulated_readings():
    connection = sqlite3.connect(":memory:")
    _create_tables(connection)

    sites = pd.DataFrame(
        [
            {
                "site_id": "S001",
                "site_name": "Example Site",
                "country": "USA",
                "city": "Chicago",
                "site_type": "Factory",
            }
        ]
    )
    machines = pd.DataFrame(
        [
            {
                "machine_id": "M001",
                "site_id": "S001",
                "machine_name": "Example Machine",
                "machine_type": "Press",
                "department": "Assembly",
                "installation_year": 2020,
                "status": "Active",
            }
        ]
    )
    production_data = pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 08:00:00",
                "machine_id": "M001",
                "output_units": 100,
                "defect_units": 2,
                "downtime_minutes": 5,
            }
        ]
    )
    energy_data = pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 08:00:00",
                "machine_id": "M001",
                "temperature": 75,
                "energy_kwh": 12,
                "vibration": 0.2,
            }
        ]
    )

    try:
        load_data(connection, sites, machines, production_data, energy_data)
        load_data(connection, sites, machines, production_data, energy_data)

        connection.execute(
            """
            INSERT INTO production_data (
                timestamp, machine_id, output_units, defect_units, downtime_minutes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-01-01 08:00:10", "M001", 120, 1, 0),
        )
        connection.execute(
            """
            INSERT INTO energy_data (
                timestamp, machine_id, temperature, energy_kwh, vibration
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-01-01 08:00:10", "M001", 76, 13, 0.25),
        )

        load_data(connection, sites, machines, production_data, energy_data)

        production_rows = connection.execute(
            """
            SELECT timestamp, output_units
            FROM production_data
            ORDER BY timestamp
            """
        ).fetchall()
        energy_rows = connection.execute(
            """
            SELECT timestamp, temperature
            FROM energy_data
            ORDER BY timestamp
            """
        ).fetchall()

        assert production_rows == [
            ("2026-01-01 08:00:00", 100.0),
            ("2026-01-01 08:00:10", 120.0),
        ]
        assert energy_rows == [
            ("2026-01-01 08:00:00", 75.0),
            ("2026-01-01 08:00:10", 76.0),
        ]
    finally:
        connection.close()