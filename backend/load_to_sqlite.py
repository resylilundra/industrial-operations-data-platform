from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATABASE_PATH = PROJECT_ROOT / "data" / "industrial_operations.db"


def main():
    # Load validated records only.
    sites = pd.read_csv(PROCESSED_DIR / "sites_clean.csv")
    machines = pd.read_csv(PROCESSED_DIR / "machines_clean.csv")
    production_data = pd.read_csv(PROCESSED_DIR / "production_data_clean.csv")
    energy_data = pd.read_csv(PROCESSED_DIR / "energy_data_clean.csv")
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        # SQLite does not enforce foreign keys unless this is enabled.
        connection.execute("PRAGMA foreign_keys = ON;")

        cursor = connection.cursor()

        # Child tables must be dropped before their parent tables.
        cursor.executescript("""
            DROP TABLE IF EXISTS energy_data;
            DROP TABLE IF EXISTS production_data;
            DROP TABLE IF EXISTS machines;
            DROP TABLE IF EXISTS sites;

            CREATE TABLE sites (
                site_id TEXT PRIMARY KEY,
                site_name TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                site_type TEXT NOT NULL
            );

            CREATE TABLE machines (
                machine_id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                machine_name TEXT NOT NULL,
                machine_type TEXT NOT NULL,
                department TEXT NOT NULL,
                installation_year INTEGER NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (site_id) REFERENCES sites(site_id)
            );

            CREATE TABLE production_data (
                production_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                machine_id TEXT NOT NULL,
                output_units REAL NOT NULL CHECK (output_units >= 0),
                defect_units REAL NOT NULL CHECK (defect_units >= 0),
                downtime_minutes REAL NOT NULL CHECK (downtime_minutes >= 0),
                UNIQUE (machine_id, timestamp),
                FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
            );

            CREATE TABLE energy_data (
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

        # Insert parents before children, preserving foreign-key integrity.
        sites.to_sql("sites", connection, if_exists="append", index=False)
        machines.to_sql("machines", connection, if_exists="append", index=False)
        production_data.to_sql(
            "production_data",
            connection,
            if_exists="append",
            index=False,
        )
        energy_data.to_sql(
            "energy_data",
            connection,
            if_exists="append",
            index=False,
        )

        # Confirm the expected row totals.
        expected_counts = {
            "sites": 3,
            "machines": 3,
            "production_data": 6,
            "energy_data": 6,
        }

        print("Load complete:\n")

        for table_name, expected_count in expected_counts.items():
            row_count = connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            print(
                f"{table_name}: {row_count} row(s) loaded "
                f"(expected: {expected_count})"
            )

            if row_count != expected_count:
                raise ValueError(
                    f"Unexpected row count for {table_name}: "
                    f"{row_count}, expected {expected_count}"
                )

        connection.commit()
        print(f"\nSQLite database created successfully: {DATABASE_PATH}")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
