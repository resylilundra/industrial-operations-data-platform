import random
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from backend.database import get_connection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_BATCH_DIR = PROJECT_ROOT / "data_lake" / "raw"


def write_batch_files(production_records, energy_records, batch_id, raw_dir):
    production_dir = raw_dir / "production"
    energy_dir = raw_dir / "energy"

    production_dir.mkdir(parents=True, exist_ok=True)
    energy_dir.mkdir(parents=True, exist_ok=True)

    production_path = production_dir / f"production_{batch_id}.csv"
    energy_path = energy_dir / f"energy_{batch_id}.csv"

    pd.DataFrame(production_records).to_csv(production_path, index=False)
    pd.DataFrame(energy_records).to_csv(energy_path, index=False)

    return production_path, energy_path


def main():
    connection = get_connection()

    try:
        machine_rows = connection.execute(
            "SELECT machine_id FROM machines WHERE status = ?",
            ("Active",),
        ).fetchall()
        machine_ids = [row["machine_id"] for row in machine_rows]

        if not machine_ids:
            raise RuntimeError("No active machines found in the database.")
        print("Generating simulated readings every 10 seconds. Press Ctrl+C to stop.")

        while True:
            now = datetime.now(timezone.utc)
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            batch_id = now.strftime("%Y%m%dT%H%M%SZ")
            production_records = []
            energy_records = []

            for machine_id in machine_ids:
                output_units = random.randint(80, 200)
                defect_units = random.randint(0, min(5, output_units))
                downtime_minutes = random.choice([0, 0, 0, 1, 2])

                temperature = round(random.uniform(55, 95), 1)
                energy_kwh = round(random.uniform(10, 25), 2)
                vibration = round(random.uniform(0.1, 0.4), 2)

                production_record = {
                    "timestamp": timestamp,
                    "machine_id": machine_id,
                    "output_units": output_units,
                    "defect_units": defect_units,
                    "downtime_minutes": downtime_minutes,
                }
                energy_record = {
                    "timestamp": timestamp,
                    "machine_id": machine_id,
                    "temperature": temperature,
                    "energy_kwh": energy_kwh,
                    "vibration": vibration,
                }

                production_records.append(production_record)
                energy_records.append(energy_record)

                connection.execute(
                    """
                    INSERT INTO production_data (
                        timestamp, machine_id, output_units,
                        defect_units, downtime_minutes
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        machine_id,
                        output_units,
                        defect_units,
                        downtime_minutes,
                    ),
                )

                connection.execute(
                    """
                    INSERT INTO energy_data (
                        timestamp, machine_id, temperature, energy_kwh, vibration
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        machine_id,
                        temperature,
                        energy_kwh,
                        vibration,
                    ),
                )

            production_path, energy_path = write_batch_files(
                production_records,
                energy_records,
                batch_id,
                RAW_BATCH_DIR,
            )
            print(f"Saved raw batches: {production_path} and {energy_path}")

            connection.commit()
            print(f"Added readings for {len(machine_ids)} machine(s) at {timestamp}")
            time.sleep(10)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
