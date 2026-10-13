from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_get_machines_returns_successful_response():
    response = client.get("/machines")

    assert response.status_code == 200

    machines = response.json()
    assert isinstance(machines, list)

    if machines:
        assert "machine_id" in machines[0]
        assert "site_id" in machines[0]


def test_get_production_returns_successful_response():
    response = client.get("/production")

    assert response.status_code == 200

    production_records = response.json()
    assert isinstance(production_records, list)

    if production_records:
        assert "timestamp" in production_records[0]
        assert "machine_id" in production_records[0]
        assert "output_units" in production_records[0]


def test_get_energy_returns_successful_response():
    response = client.get("/energy")

    assert response.status_code == 200

    energy_records = response.json()
    assert isinstance(energy_records, list)

    if energy_records:
        assert "timestamp" in energy_records[0]
        assert "machine_id" in energy_records[0]
        assert "temperature" in energy_records[0]


def test_get_total_output_returns_number():
    response = client.get("/kpis/total-output")

    assert response.status_code == 200
    assert isinstance(response.json(), (int, float))


def test_get_average_temperature_returns_number_or_null():
    response = client.get("/kpis/average-temperature")

    assert response.status_code == 200
    assert response.json() is None or isinstance(response.json(), (int, float))
