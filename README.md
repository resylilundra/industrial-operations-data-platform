# Industrial Operations Data Platform

A Python prototype that takes industrial operations data from CSV files through
validation and SQLite storage, then exposes it through a FastAPI service and a
live Streamlit dashboard. It also includes a simulator for generating
time-stamped production and energy readings.

## Current progress

### Implemented

- Normalize column names, trim whitespace, standardize IDs, and correct the
  documented site ID typo `SO01` to `S001`.
- Validate sites, machines, production records, and energy records.
- Save clean and rejected CSV files, including rejection reasons.
- Write a JSON validation summary with accepted/rejected row counts and logged
  corrections.
- Load clean records into SQLite with primary keys, checks, unique constraints,
  and foreign keys.
- Provide FastAPI endpoints for machine, production, and energy records; five
  KPIs; and per-machine production performance.
- Filter KPIs and performance readings by all-time or last-hour period.
- Display KPI values, machine/production/energy tables, and per-machine output
  and defect-rate charts in a Streamlit dashboard that refreshes every
  10 seconds.
- Generate simulated production and energy readings for active machines every
  10 seconds.
- Test validation rules, SQL queries, SQLite foreign-key enforcement, and API
  endpoints with pytest. Query tests use an in-memory database, and API tests
  use a temporary SQLite database with seeded sample records.

## Data and validation

Put the source CSV files in `data/raw/` with these names:

- `sites.csv`
- `machines.csv`
- `production_data.csv`
- `energy_data.csv`

From the project root, run the validation step:

```bash
python -m backend.validate_data
```

The script leaves raw files unchanged and writes:

- Accepted rows to `data/processed/*_clean.csv`
- Rejected rows, with a `rejection_reason` column, to
  `data/rejected/*_rejected.csv`
- Row counts and automatic corrections to
  `data/reports/validation_summary.json`

Then load the clean CSV files into SQLite:

```bash
python -m backend.load_to_sqlite
```

The database is written to `data/industrial_operations.db`. The loader drops
and recreates its four tables each time it runs, so existing table contents
are replaced. Run validation first so the clean CSV files are up to date.

See [docs/data_quality_policy.md](docs/data_quality_policy.md) for the current
cleaning and rejection rules.

## Setup

Create and activate a virtual environment from the project root:

```bash
python -m venv venv
```

On macOS or Linux (including WSL):

```bash
source venv/bin/activate
```

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the tests

Run all tests from the project root:

```bash
python -m pytest -v
```

The tests use small sample DataFrames and temporary/in-memory SQLite databases.
They do not need the project CSV files or modify the saved project database.
The API fixture seeds one site, one machine, and production/energy readings;
the KPI tests assert the exact calculated values. To show captured test output,
use:

```bash
python -m pytest -v -s
```

The current tests cover duplicate machine IDs, unknown site IDs, negative
production output, out-of-range temperature, SQLite rejection of a machine
that references a site that does not exist, query calculations, and API
responses. Loader tests also verify that repeating a CSV load does not
duplicate readings or remove additional simulated readings.

## Run the API and dashboard

Run data validation and load the clean data into SQLite first if the database
does not exist yet or the source CSV data has changed:

```bash
python -m backend.validate_data
python -m backend.load_to_sqlite
```

Start the API from the project root:

```bash
python -m uvicorn backend.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Its interactive documentation
is at `http://127.0.0.1:8000/docs`.

Available endpoints:

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/machines` | Machine records |
| GET | `/production` | Production records |
| GET | `/energy` | Energy records |
| GET | `/kpis/total-output` | Sum of production output |
| GET | `/kpis/average-temperature` | Average temperature, or `null` if there is no energy data |
| GET | `/kpis/defect-rate` | Defect units as a percentage of total output, or `null` if there is no output |
| GET | `/kpis/energy-per-unit` | Total energy in kWh divided by total output, or `null` if there is no output |
| GET | `/kpis/total-downtime` | Sum of production downtime in minutes |
| GET | `/production/performance` | Timestamped output and defect-rate percentage for each machine |

All KPI endpoints and `/production/performance` accept the optional `period`
query parameter:

- `period=all_time` (default): include all readings.
- `period=last_hour`: include readings from the previous hour.

For example: `http://127.0.0.1:8000/kpis/total-output?period=last_hour`.

Keep the API running. Open a second terminal, activate the same virtual
environment, and start the Streamlit dashboard:

```bash
python -m streamlit run dashboard/streamlit_app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`. The
dashboard requests data from the API, shows the KPI values and time-series
charts, and displays machine, production, and energy records in tables. Its
period selector applies to the KPIs and machine-performance charts. Keep both
terminals running while using the dashboard. Stop either service with `Ctrl+C`
in its terminal.

## Simulate live readings

The simulator requires an initialized database containing at least one active
machine. Start it from another terminal in the project root:

```bash
python -m backend.simulate_data
```

It appends one production reading and one energy reading per active machine
every 10 seconds. The dashboard refreshes on the same interval. Stop the
simulator with `Ctrl+C`.

The loader creates tables only when they do not already exist, updates existing
site and machine details from the CSV files, and skips production or energy
readings whose machine and timestamp are already present. This lets you rerun
`python -m backend.load_to_sqlite` without deleting accumulated simulator
readings. When a CSV reading has the same machine and timestamp as a reading
already stored, the existing reading is kept.

## Project structure

```text
industrial-operations-data-platform/
├── backend/
│   ├── load_to_sqlite.py
│   ├── validate_data.py
│   ├── database.py          # SQLite connection helper
│   ├── main.py              # FastAPI application and endpoints
│   ├── queries.py           # SQL queries and KPI calculations
│   └── simulate_data.py     # Periodic sample-reading generator
├── dashboard/
│   └── streamlit_app.py     # Streamlit dashboard
├── data/
│   ├── raw/
│   ├── processed/
│   ├── rejected/
│   ├── reports/
│   └── industrial_operations.db
├── docs/
│   └── data_quality_policy.md
├── tests/
│   ├── test_api.py
│   ├── test_queries.py
│   └── test_validate_data.py
└── requirements.txt
```
