from urllib import response

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.load_to_sqlite import _create_tables
from backend.main import app
@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database_path = tmp_path / "test_database.db"

    # Make the API's database helper use this test's temporary database.
    monkeypatch.setattr(database, "DATABASE_PATH", test_database_path)

    connection = database.get_connection()
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
        connection.execute(
            """
            INSERT INTO energy_data (
                timestamp, machine_id, temperature, energy_kwh, vibration
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-01-01 08:00:00", "M001", 75, 12, 0.2),
        )
        connection.commit()
    finally:
        connection.close()

    with TestClient(app) as test_client:
        yield test_client

def test_get_machines_returns_successful_response(client):
    response = client.get("/machines")

    assert response.status_code == 200

    machines = response.json()
    assert isinstance(machines, list)

    if machines:
        assert "machine_id" in machines[0]
        assert "site_id" in machines[0]


def test_get_production_returns_successful_response(client):
    response = client.get("/production")

    assert response.status_code == 200

    production_records = response.json()
    assert isinstance(production_records, list)

    if production_records:
        assert "timestamp" in production_records[0]
        assert "machine_id" in production_records[0]
        assert "output_units" in production_records[0]


def test_get_energy_returns_successful_response(client):
    response = client.get("/energy")

    assert response.status_code == 200

    energy_records = response.json()
    assert isinstance(energy_records, list)

    if energy_records:
        assert "timestamp" in energy_records[0]
        assert "machine_id" in energy_records[0]
        assert "temperature" in energy_records[0]


def test_get_total_output_returns_number(client):
    response = client.get("/kpis/total-output")

    assert response.status_code == 200
    assert response.json() == 100

def test_get_average_temperature_returns_number_or_null(client):
    response = client.get("/kpis/average-temperature")

    assert response.status_code == 200
    assert response.json() == 75


def test_get_defect_rate_returns_number_or_null(client):
    response = client.get("/kpis/defect-rate")

    assert response.status_code == 200
    assert response.json() == 2


def test_get_energy_per_unit_returns_number_or_null(client):
    response = client.get("/kpis/energy-per-unit")

    assert response.status_code == 200
    assert response.json()  == pytest.approx(0.12)


def test_get_total_downtime_returns_number(client):
    response = client.get("/kpis/total-downtime")

    assert response.status_code == 200
    assert response.json() == 5

def test_get_machine_performance_returns_rows(client):
    response = client.get(
        "/production/performance",
        params={"period": "all_time"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "timestamp": "2026-01-01 08:00:00",
            "machine_id": "M001",
            "output_units": 100.0,
            "defect_rate_percent": 2.0,
        }
    ]