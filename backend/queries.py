import sqlite3


def get_all_machines(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT machine_id, site_id, machine_name, machine_type,
               department, installation_year, status
        FROM machines
        ORDER BY machine_id
        """
    ).fetchall()

    return [dict(row) for row in rows]


def get_all_production_data(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT timestamp, machine_id, output_units, defect_units, downtime_minutes
        FROM production_data
        ORDER BY timestamp
        """
    ).fetchall()

    return [dict(row) for row in rows]


def get_all_energy_data(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT timestamp, machine_id, temperature, energy_kwh, vibration
        FROM energy_data
        ORDER BY timestamp
        """
    ).fetchall()

    return [dict(row) for row in rows]


def get_total_output(connection: sqlite3.Connection) -> float:
    row = connection.execute(
        """
        SELECT COALESCE(SUM(output_units), 0)
        FROM production_data
        """
    ).fetchone()

    return row[0]


def get_average_temperature(connection: sqlite3.Connection) -> float | None:
    row = connection.execute(
        """
        SELECT AVG(temperature)
        FROM energy_data
        """
    ).fetchone()

    return row[0]