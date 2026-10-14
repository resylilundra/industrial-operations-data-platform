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


def get_total_output(
    connection: sqlite3.Connection,
    period: str = "all_time",
) -> float:
    period_condition = _period_condition(period)
    row = connection.execute(
        f"""
        SELECT COALESCE(SUM(output_units), 0)
        FROM production_data
        WHERE {period_condition}
        """
    ).fetchone()

    return row[0]


def _period_condition(period: str) -> str:
    if period == "all_time":
        return "1 = 1"
    if period == "last_hour":
        return "datetime(timestamp) >= datetime('now', '-1 hour')"
    raise ValueError(f"Unsupported period: {period}")


def get_average_temperature(
    connection: sqlite3.Connection,
    period: str = "all_time",
) -> float | None:
    period_condition = _period_condition(period)
    row = connection.execute(
        f"""
        SELECT AVG(temperature)
        FROM energy_data
        WHERE {period_condition}
        """
    ).fetchone()

    return row[0]


def get_defect_rate(
    connection: sqlite3.Connection,
    period: str = "all_time",
) -> float | None:
    period_condition = _period_condition(period)
    row = connection.execute(
        f"""
        SELECT
            100.0 * COALESCE(SUM(defect_units), 0)
            / NULLIF(COALESCE(SUM(output_units), 0), 0)
        FROM production_data
        WHERE {period_condition}
        """
    ).fetchone()

    return row[0]


def get_energy_per_unit(
    connection: sqlite3.Connection,
    period: str = "all_time",
) -> float | None:
    period_condition = _period_condition(period)
    row = connection.execute(
        f"""
        SELECT
            (
                SELECT COALESCE(SUM(energy_kwh), 0)
                FROM energy_data
                WHERE {period_condition}
            )
            / NULLIF(
                (
                    SELECT COALESCE(SUM(output_units), 0)
                    FROM production_data
                    WHERE {period_condition}
                ),
                0
            )
        """
    ).fetchone()

    return row[0]


def get_total_downtime(
    connection: sqlite3.Connection,
    period: str = "all_time",
) -> float:
    period_condition = _period_condition(period)
    row = connection.execute(
        f"""
        SELECT COALESCE(SUM(downtime_minutes), 0)
        FROM production_data
        WHERE {period_condition}
        """
    ).fetchone()

    return row[0]

def get_machine_performance(
    connection: sqlite3.Connection,
    period: str = "all_time",
) -> list[dict]:
    period_condition = _period_condition(period)
    rows = connection.execute(
        f"""
        SELECT
            timestamp,
            machine_id,
            output_units,
            CASE
                WHEN output_units = 0 THEN NULL
                ELSE 100.0 * defect_units / output_units
            END AS defect_rate_percent
        FROM production_data
        WHERE {period_condition}
        ORDER BY timestamp, machine_id
        """
    ).fetchall()

    return [dict(row) for row in rows]