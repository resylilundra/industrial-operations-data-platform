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
  10 seconds. KPI values can come from the original SQLite API or the
  Parquet/DuckDB data lake, with the selected source labelled in the dashboard.
- Generate simulated production and energy readings for active machines every
  10 seconds.
- Upload raw batches to a local S3-compatible MinIO bucket, validate production
  and energy batches, and write accepted rows to date-partitioned Parquet files
  while retaining rejected rows and their reasons.
- Query the Parquet datasets with DuckDB for total output, defect rate, total
  downtime, average temperature, and energy per output unit. Exact duplicate
  readings count once; conflicting duplicates are reported as errors.
- Orchestrate MinIO discovery, validation, and Parquet/rejection writes with
  Prefect. Successfully processed object versions are recorded locally so
  repeated scheduled runs skip them; new object versions and new batches are
  processed.
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

The database is written to `data/industrial_operations.db`. The loader creates
tables if they do not already exist, updates matching site and machine records,
and skips duplicate production and energy readings. This preserves existing
simulator readings. Run validation first so the clean CSV files are up to date.

See [docs/data_quality_policy.md](docs/data_quality_policy.md) for the current
cleaning and rejection rules.

## Query Parquet KPIs

After processing production and energy batches from MinIO into
`data_lake/processed/`, run the DuckDB KPI queries from the project root:

```bash
python -m backend.query_parquet
```

The script reads the date-partitioned production and energy Parquet files and
prints total output, defect rate, total downtime, average temperature, and
energy per output unit. Exact duplicate readings count once, and conflicting
readings for the same machine and timestamp raise an error rather than
silently inflating or changing a KPI.

## Local data-lake pipeline

This extension uses local S3-compatible object storage and local files; it is
not a cloud deployment.

```text
Synthetic simulator / CSV batches
              |
              v
      MinIO / AIStor bucket
              |
              v
  Prefect flow: discover objects
       -> read and validate
       -> record processed version
              |
       +------+------+
       |             |
       v             v
Partitioned       Rejected CSVs
Parquet files     with reasons
       |
       v
 DuckDB KPI queries ---> Streamlit KPI source selector

Existing CSV -> SQLite -> FastAPI -> Streamlit tables/charts and SQLite KPIs
```

### Configure MinIO / AIStor

Start Docker Desktop with WSL integration enabled. If you already created the
local AIStor container, start it from WSL:

```bash
docker start aistor-server
```

The container should expose the S3 endpoint at `http://localhost:9000` and the
console at `http://localhost:9001`. Configure a MinIO client alias using the
credentials configured for your server, then create the bucket if it does not
exist:

```bash
mc alias set localminio http://localhost:9000 YOUR_ACCESS_KEY YOUR_SECRET_KEY
mc mb --ignore-existing localminio/industrial-operations
```

Upload a batch of each type (replace the local file paths with your batch CSV
paths):

```bash
mc cp path/to/production_batch.csv localminio/industrial-operations/raw/production/
mc cp path/to/energy_batch.csv localminio/industrial-operations/raw/energy/
```

Do not put real credentials or an AIStor license in source control. AIStor
requires its own license; follow its current vendor setup instructions when
creating a new container. The pipeline only needs the configured S3 endpoint
and credentials.

### Run Prefect

Use separate WSL terminals and keep the server and deployment process running.
Start the local Prefect server in the first terminal:

```bash
cd /mnt/c/Users/YOUR_USER/projects/industrial-operations-data-platform-datalake
source venv/bin/activate
python -m prefect server start
```

In the second terminal, activate the same environment and configure the
connection settings. Enter the credentials configured for your MinIO server
when prompted; the secret prompt does not echo typed characters:

```bash
cd /mnt/c/Users/YOUR_USER/projects/industrial-operations-data-platform-datalake
source venv/bin/activate
export PREFECT_API_URL="http://127.0.0.1:4200/api"
export MINIO_ENDPOINT_URL="http://localhost:9000"
read -r -p "MinIO access key: " MINIO_ACCESS_KEY
export MINIO_ACCESS_KEY
read -r -s -p "MinIO secret key: " MINIO_SECRET_KEY
echo
export MINIO_SECRET_KEY
```

Start the hourly deployment from the second terminal:

```bash
python -m backend.prefect_pipeline
```

The flow is scheduled at the start of each hour. Keep this terminal, the
Prefect server, and MinIO running for scheduled runs to execute. To manually
trigger one run while connected to the server, use **Run** from the deployment
in the Prefect UI, or execute:

```bash
python -c "from backend.prefect_pipeline import run_data_lake_pipeline; run_data_lake_pipeline()"
```

Check the Prefect UI at `http://127.0.0.1:4200`. The hourly deployment scans
direct CSV objects under `raw/production/` and `raw/energy/`, validates them,
writes accepted Parquet and rejected CSV outputs, and records each successfully
processed object version in `data_lake/state/processed_batches.sqlite3`.
An unchanged object version is skipped on later runs. A new object or changed
object version is processed. If processing fails before completion, it is not
marked processed and can be retried.

### Verify reruns

Run the flow twice against the same MinIO object. The second run should log
`Skipping already processed batch`; the state registry prevents another output
write. A new batch with a new object key is still processed. Parquet filenames
are based on the batch identifier, and DuckDB also counts exact duplicate
machine/timestamp readings only once.

### Use Parquet KPIs in the dashboard

Start the existing API and Streamlit dashboard as described below. The
dashboard's **KPI data source** selector defaults to **SQLite via API**, which
preserves the existing behavior. Select **Parquet via DuckDB** to display KPIs
from the data-lake Parquet files. The selected KPI source is labelled above the
metrics. DuckDB KPIs are all-time; the period selector continues to apply to
the SQLite KPI option and machine-performance charts.

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
that references a site that does not exist, query calculations, API
responses, and batch reruns. The rerun test confirms that processing the same
object twice leaves the KPI unchanged, while a new batch adds its reading.
Loader tests also verify that repeating a CSV load does not duplicate readings
or remove additional simulated readings.

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
dashboard requests SQLite/API data for machine, production, and energy tables
and time-series charts. Its KPI source selector defaults to the existing
SQLite/API KPIs and can switch to the new Parquet/DuckDB KPIs. The period
selector applies to SQLite KPIs and machine-performance charts. Keep both
terminals running while using the dashboard. Stop either service with `Ctrl+C`
in its terminal.

## Simulate live readings

The simulator requires an initialized database containing at least one active
machine. Start it from another terminal in the project root:

```bash
python -m backend.simulate_data
```

It appends one production reading and one energy reading per active machine
every 10 seconds. These are synthetic sample readings for demonstration and
testing; they are not real factory or sensor measurements. The dashboard
refreshes on the same interval. Stop the simulator with `Ctrl+C`.

The loader creates tables only when they do not already exist, updates existing
site and machine details from the CSV files, and skips production or energy
readings whose machine and timestamp are already present. This lets you rerun
`python -m backend.load_to_sqlite` without deleting accumulated simulator
readings. When a CSV reading has the same machine and timestamp as a reading
already stored, the existing reading is kept.

## Project structure

```text
industrial-operations-data-platform-datalake/
├── backend/
│   ├── batch_state.py       # Idempotent processed-object registry
│   ├── load_to_sqlite.py
│   ├── validate_data.py
│   ├── database.py          # SQLite connection helper
│   ├── main.py              # FastAPI application and endpoints
│   ├── queries.py           # SQL queries and KPI calculations
│   ├── prefect_pipeline.py  # Scheduled MinIO-to-Parquet flow
│   ├── process_raw_batch.py # MinIO reads and validation/output
│   ├── query_parquet.py     # DuckDB KPI calculations
│   └── simulate_data.py     # Periodic synthetic-reading generator
├── dashboard/
│   └── streamlit_app.py     # Streamlit dashboard
├── data_lake/
│   ├── processed/            # Date-partitioned Parquet files
│   ├── rejected/             # Rejected batches and reasons
│   └── state/                # Local processed-object registry (ignored)
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
│   ├── test_prefect_pipeline.py
│   ├── test_process_raw_batch.py
│   ├── test_process_energy_batch.py
│   ├── test_query_parquet.py
│   ├── test_simulate_data.py
│   ├── test_queries.py
│   └── test_validate_data.py
└── requirements.txt
```

All simulator and example batch readings are synthetic. This is a local
learning prototype, not a production or large-scale cloud deployment.
