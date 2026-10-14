from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATABASE_PATH = PROJECT_ROOT / "data" / "industrial_operations.db"


def _create_tables(connection: sqlite3.Connection) -> None:
    # SQLite does not enforce foreign keys unless this is enabled.
    connection.execute("PRAGMA foreign_keys = ON;")

    connection.executescript("""
        CREATE TABLE IF NOT EXISTS sites (
            site_id TEXT PRIMARY KEY,
            site_name TEXT NOT NULL,
            country TEXT NOT NULL,
            city TEXT NOT NULL,
            site_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS machines (
            machine_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            machine_name TEXT NOT NULL,
            machine_type TEXT NOT NULL,
            department TEXT NOT NULL,
            installation_year INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (site_id) REFERENCES sites(site_id)
        );

        CREATE TABLE IF NOT EXISTS production_data (
            production_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            output_units REAL NOT NULL CHECK (output_units >= 0),
            defect_units REAL NOT NULL CHECK (defect_units >= 0),
            downtime_minutes REAL NOT NULL CHECK (downtime_minutes >= 0),
            UNIQUE (machine_id, timestamp),
            FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
        );

        CREATE TABLE IF NOT EXISTS energy_data (
            energy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            temperature REAL NOT NULL CHECK (temperature BETWEEN 0 AND 200),
            energy_kwh REAL NOT NULL CHECK (energy_kwh >= 0),
            vibration REAL NOT NULL CHECK (vibration >= 0),
            UNIQUE (machine_id, timestamp),
            FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
        );
    """)


def main():
    # Load validated records only.
    sites = pd.read_csv(PROCESSED_DIR / "sites_clean.csv")
    machines = pd.read_csv(PROCESSED_DIR / "machines_clean.csv")
    production_data = pd.read_csv(PROCESSED_DIR / "production_data_clean.csv")
    energy_data = pd.read_csv(PROCESSED_DIR / "energy_data_clean.csv")
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        _create_tables(connection)
        load_data(connection, sites, machines, production_data, energy_data)

        print("Load complete. Current database row totals:\n")

        for table_name in ("sites", "machines", "production_data", "energy_data"):
            row_count = connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            print(f"{table_name}: {row_count} row(s)")

        connection.commit()
        print(f"\nSQLite database created successfully: {DATABASE_PATH}")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def load_data(
    connection: sqlite3.Connection,
    sites: pd.DataFrame,
    machines: pd.DataFrame,
    production_data: pd.DataFrame,
    energy_data: pd.DataFrame,
) -> None:
    site_columns = ("site_id", "site_name", "country", "city", "site_type")
    connection.executemany(
        """
        INSERT INTO sites (site_id, site_name, country, city, site_type)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(site_id) DO UPDATE SET
            site_name = excluded.site_name,
            country = excluded.country,
            city = excluded.city,
            site_type = excluded.site_type
        """,
        [
            tuple(row[column] for column in site_columns)
            for row in sites.to_dict(orient="records")
        ],
    )

    machine_columns = (
        "machine_id",
        "site_id",
        "machine_name",
        "machine_type",
        "department",
        "installation_year",
        "status",
    )
    connection.executemany(
        """
        INSERT INTO machines (
            machine_id, site_id, machine_name, machine_type,
            department, installation_year, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(machine_id) DO UPDATE SET
            site_id = excluded.site_id,
            machine_name = excluded.machine_name,
            machine_type = excluded.machine_type,
            department = excluded.department,
            installation_year = excluded.installation_year,
            status = excluded.status
        """,
        [
            tuple(row[column] for column in machine_columns)
            for row in machines.to_dict(orient="records")
        ],
    )

    production_columns = (
        "timestamp",
        "machine_id",
        "output_units",
        "defect_units",
        "downtime_minutes",
    )
    connection.executemany(
        """
        INSERT INTO production_data (
            timestamp, machine_id, output_units, defect_units, downtime_minutes
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(machine_id, timestamp) DO NOTHING
        """,
        [
            tuple(row[column] for column in production_columns)
            for row in production_data.to_dict(orient="records")
        ],
    )

    energy_columns = (
        "timestamp",
        "machine_id",
        "temperature",
        "energy_kwh",
        "vibration",
    )
    connection.executemany(
        """
        INSERT INTO energy_data (
            timestamp, machine_id, temperature, energy_kwh, vibration
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(machine_id, timestamp) DO NOTHING
        """,
        [
            tuple(row[column] for column in energy_columns)
            for row in energy_data.to_dict(orient="records")
        ],
    )


if __name__ == "__main__":
    main()
