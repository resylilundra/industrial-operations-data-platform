from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_PARQUET_GLOB = str(
    PROJECT_ROOT
    / "data_lake"
    / "processed"
    / "production"
    / "**"
    / "*.parquet"
)
ENERGY_PARQUET_GLOB = str(
    PROJECT_ROOT
    / "data_lake"
    / "processed"
    / "energy"
    / "**"
    / "*.parquet"
)


def get_total_output(parquet_glob: str) -> float:
    connection = duckdb.connect(":memory:")
    try:
        conflicting_keys = connection.execute(
            """
            SELECT machine_id, timestamp
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    output_units,
                    defect_units,
                    downtime_minutes
                FROM read_parquet(?)
            ) AS distinct_readings
            GROUP BY machine_id, timestamp
            HAVING COUNT(*) > 1
            ORDER BY machine_id, timestamp
            """,
            [parquet_glob],
        ).fetchall()

        if conflicting_keys:
            keys = ", ".join(
                f"{machine_id} at {timestamp}"
                for machine_id, timestamp in conflicting_keys
            )
            raise ValueError(
                f"Conflicting duplicate production readings: {keys}"
            )

        row = connection.execute(
            """
            SELECT COALESCE(SUM(output_units), 0)
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    output_units,
                    defect_units,
                    downtime_minutes
                FROM read_parquet(?)
            ) AS distinct_readings
            """,
            [parquet_glob],
        ).fetchone()

        return row[0]
    finally:
        connection.close() 
def get_defect_rate(parquet_glob: str) -> float | None:
    connection = duckdb.connect(":memory:")
    try:
        conflicting_keys = connection.execute(
            """
            SELECT machine_id, timestamp
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    output_units,
                    defect_units,
                    downtime_minutes
                FROM read_parquet(?)
            ) AS distinct_readings
            GROUP BY machine_id, timestamp
            HAVING COUNT(*) > 1
            ORDER BY machine_id, timestamp
            """,
            [parquet_glob],
        ).fetchall()

        if conflicting_keys:
            keys = ", ".join(
                f"{machine_id} at {timestamp}"
                for machine_id, timestamp in conflicting_keys
            )
            raise ValueError(
                f"Conflicting duplicate production readings: {keys}"
            )

        row = connection.execute(
            """
            SELECT
                100.0 * COALESCE(SUM(defect_units), 0)
                / NULLIF(COALESCE(SUM(output_units), 0), 0)
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    output_units,
                    defect_units,
                    downtime_minutes
                FROM read_parquet(?)
            ) AS distinct_readings
            """,
            [parquet_glob],
        ).fetchone()

        return row[0]
    finally:
        connection.close()

def get_total_downtime(parquet_glob: str) -> float:
    connection = duckdb.connect(":memory:")
    try:
        conflicting_keys = connection.execute(
            """
            SELECT machine_id, timestamp
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    output_units,
                    defect_units,
                    downtime_minutes
                FROM read_parquet(?)
            ) AS distinct_readings
            GROUP BY machine_id, timestamp
            HAVING COUNT(*) > 1
            ORDER BY machine_id, timestamp
            """,
            [parquet_glob],
        ).fetchall()

        if conflicting_keys:
            keys = ", ".join(
                f"{machine_id} at {timestamp}"
                for machine_id, timestamp in conflicting_keys
            )
            raise ValueError(
                f"Conflicting duplicate production readings: {keys}"
            )

        row = connection.execute(
            """
            SELECT COALESCE(SUM(downtime_minutes), 0)
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    output_units,
                    defect_units,
                    downtime_minutes
                FROM read_parquet(?)
            ) AS distinct_readings
            """,
            [parquet_glob],
        ).fetchone()

        return row[0]
    finally:
        connection.close()


def get_average_temperature(parquet_glob: str) -> float | None:
    connection = duckdb.connect(":memory:")
    try:
        conflicting_keys = connection.execute(
            """
            SELECT machine_id, timestamp
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    temperature,
                    energy_kwh,
                    vibration
                FROM read_parquet(?)
            ) AS distinct_readings
            GROUP BY machine_id, timestamp
            HAVING COUNT(*) > 1
            ORDER BY machine_id, timestamp
            """,
            [parquet_glob],
        ).fetchall()

        if conflicting_keys:
            keys = ", ".join(
                f"{machine_id} at {timestamp}"
                for machine_id, timestamp in conflicting_keys
            )
            raise ValueError(f"Conflicting duplicate energy readings: {keys}")

        row = connection.execute(
            """
            SELECT AVG(temperature)
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    temperature,
                    energy_kwh,
                    vibration
                FROM read_parquet(?)
            ) AS distinct_readings
            """,
            [parquet_glob],
        ).fetchone()

        return row[0]
    finally:
        connection.close()


def get_energy_per_unit(
    production_parquet_glob: str,
    energy_parquet_glob: str,
) -> float | None:
    connection = duckdb.connect(":memory:")
    try:
        conflicting_production_keys = connection.execute(
            """
            SELECT machine_id, timestamp
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    output_units,
                    defect_units,
                    downtime_minutes
                FROM read_parquet(?)
            ) AS distinct_readings
            GROUP BY machine_id, timestamp
            HAVING COUNT(*) > 1
            ORDER BY machine_id, timestamp
            """,
            [production_parquet_glob],
        ).fetchall()

        if conflicting_production_keys:
            keys = ", ".join(
                f"{machine_id} at {timestamp}"
                for machine_id, timestamp in conflicting_production_keys
            )
            raise ValueError(f"Conflicting duplicate production readings: {keys}")

        conflicting_energy_keys = connection.execute(
            """
            SELECT machine_id, timestamp
            FROM (
                SELECT DISTINCT
                    machine_id,
                    timestamp,
                    temperature,
                    energy_kwh,
                    vibration
                FROM read_parquet(?)
            ) AS distinct_readings
            GROUP BY machine_id, timestamp
            HAVING COUNT(*) > 1
            ORDER BY machine_id, timestamp
            """,
            [energy_parquet_glob],
        ).fetchall()

        if conflicting_energy_keys:
            keys = ", ".join(
                f"{machine_id} at {timestamp}"
                for machine_id, timestamp in conflicting_energy_keys
            )
            raise ValueError(f"Conflicting duplicate energy readings: {keys}")

        row = connection.execute(
            """
            SELECT
                (
                    SELECT SUM(energy_kwh)
                    FROM (
                        SELECT DISTINCT
                            machine_id,
                            timestamp,
                            temperature,
                            energy_kwh,
                            vibration
                        FROM read_parquet(?)
                    ) AS distinct_energy_readings
                )
                /
                NULLIF(
                    (
                        SELECT SUM(output_units)
                        FROM (
                            SELECT DISTINCT
                                machine_id,
                                timestamp,
                                output_units,
                                defect_units,
                                downtime_minutes
                            FROM read_parquet(?)
                        ) AS distinct_production_readings
                    ),
                    0
                )
            """,
            [energy_parquet_glob, production_parquet_glob],
        ).fetchone()

        return row[0]
    finally:
        connection.close()


def get_parquet_kpis(
    production_parquet_glob: str = PRODUCTION_PARQUET_GLOB,
    energy_parquet_glob: str = ENERGY_PARQUET_GLOB,
) -> dict[str, float | None]:
    return {
        "total_output": get_total_output(production_parquet_glob),
        "defect_rate": get_defect_rate(production_parquet_glob),
        "total_downtime": get_total_downtime(production_parquet_glob),
        "average_temperature": get_average_temperature(energy_parquet_glob),
        "energy_per_unit": get_energy_per_unit(
            production_parquet_glob,
            energy_parquet_glob,
        ),
    }


if __name__ == "__main__":
    print(f"Total output: {get_total_output(PRODUCTION_PARQUET_GLOB)}")
    print(f"Defect rate: {get_defect_rate(PRODUCTION_PARQUET_GLOB)}")
    print(f"Total downtime: {get_total_downtime(PRODUCTION_PARQUET_GLOB)}")
    print(f"Average temperature: {get_average_temperature(ENERGY_PARQUET_GLOB)}")
    print(
        "Energy per unit: "
        f"{get_energy_per_unit(PRODUCTION_PARQUET_GLOB, ENERGY_PARQUET_GLOB)}"
    )
