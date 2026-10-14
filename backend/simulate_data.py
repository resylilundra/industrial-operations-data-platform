import random
import time
from datetime import datetime, timezone

from backend.database import get_connection

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
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            for machine_id in machine_ids:
                output_units = random.randint(80, 200)
                defect_units = random.randint(0, min(5, output_units))
                downtime_minutes = random.choice([0, 0, 0, 1, 2])

                temperature = round(random.uniform(55, 95), 1)
                energy_kwh = round(random.uniform(10, 25), 2)
                vibration = round(random.uniform(0.1, 0.4), 2)

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

            connection.commit()

            print(f"Added readings for {len(machine_ids)} machine(s) at {timestamp}")
            time.sleep(10)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
