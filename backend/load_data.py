from pathlib import Path  
import pandas as pd

DATA_DIR = Path("data")

FILES = [
    "sites.csv",
    "machines.csv",
    "production_data.csv",
    "energy_data.csv",
]

def load_csv(filename):
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    data = pd.read_csv(file_path)

    print(f"\n--- {filename} ---")
    print(f"Rows: {len(data)}")
    print(f"Columns: {list(data.columns)}")
    print("\nFirst five rows:")
    print(data.head())
    print("\nMissingvalues:")
    print(data.isnull().sum())

    return data 

if __name__ == "__main__":
    datasets = {}

    for filename in FILES:
        datasets[filename] = load_csv(filename)
    sites =  datasets["sites.csv"]
    machines = datasets["machines.csv"]
    production = datasets["production_data.csv"]
    energy = datasets["energy_data.csv"]

    print("\nAll CSV files loaded successfully.")
'''
 if __name__ == "__main__":
    sites =  load_csv("sites.csv")
    machines = load_csv("machines.csv")
    production = load_csv("production_data.csv")
    energy = load_csv("energy_data.csv")

    print("\nAll CSV files loaded successfully.")
'''


