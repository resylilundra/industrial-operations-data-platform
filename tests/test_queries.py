import sqlite3

from backend.load_to_sqlite import _create_tables
from backend.queries import (
    get_all_energy_data,
    get_all_machines,
    get_all_production_data,
    get_average_temperature,
    get_total_output,
)


def test_queries_return_machine_and_production_rows():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    try:
        _create_tables(connection)

        # Add a site and machine first because the tables enforce foreign keys.
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
        connection.execute(
            """
            INSERT INTO energy_data (
                timestamp, machine_id, temperature, energy_kwh, vibration
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-01-01 08:00:00", "M001", 75, 12, 0.2),
        )
        connection.execute(
            """
            INSERT INTO energy_data (
                timestamp, machine_id, temperature, energy_kwh, vibration
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-01-01 09:00:00", "M001", 85, 14, 0.3),
        )

        machines = get_all_machines(connection)
        production = get_all_production_data(connection)
        energy = get_all_energy_data(connection)

        assert machines == [
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
        assert production == [
            {
                "timestamp": "2026-01-01 08:00:00",
                "machine_id": "M001",
                "output_units": 100.0,
                "defect_units": 2.0,
                "downtime_minutes": 5.0,
            }
        ]
        assert energy == [
            {
                "timestamp": "2026-01-01 08:00:00",
                "machine_id": "M001",
                "temperature": 75.0,
                "energy_kwh": 12.0,
                "vibration": 0.2,
            },
            {
                "timestamp": "2026-01-01 09:00:00",
                "machine_id": "M001",
                "temperature": 85.0,
                "energy_kwh": 14.0,
                "vibration": 0.3,
            },
        ]
        assert get_total_output(connection) == 100.0
        assert get_average_temperature(connection) == 80.0
    finally:
        connection.close()


def test_queries_return_expected_values_for_empty_tables():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    try:
        _create_tables(connection)

        assert get_all_machines(connection) == []
        assert get_all_production_data(connection) == []
        assert get_all_energy_data(connection) == []
        assert get_total_output(connection) == 0
        assert get_average_temperature(connection) is None
    finally:
        connection.close()
