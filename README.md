# Industrial Operations Data Platform

A Python prototype for preparing industrial operations data for analysis. The
current implementation reads CSV files, validates their contents, saves
accepted and rejected records separately, and loads accepted records into
SQLite.

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
- Provide FastAPI endpoints for machines, production records, energy records,
  total output, and average temperature.
- Display KPI values and machine, production, and energy tables in a Streamlit
  dashboard.
- Test validation rules, SQL queries, SQLite foreign-key enforcement, and API
  endpoints with pytest.

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

The tests use small in-memory DataFrames and an in-memory SQLite database, so
they do not need the project CSV files or modify the saved SQLite database.
For the printed rejected-row details and SQLite error message, turn off pytest's
output capture:

```bash
python -m pytest -v -s
```

The current tests cover duplicate machine IDs, unknown site IDs, negative
production output, out-of-range temperature, and SQLite rejection of a machine
that references a site that does not exist. Query tests use an in-memory
database. API tests currently read the project database at
`data/industrial_operations.db`.

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

Keep the API running. Open a second terminal, activate the same virtual
environment, and start the Streamlit dashboard:

```bash
python -m streamlit run dashboard/streamlit_app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`. The
dashboard requests data from the API, shows total output and average
temperature, and displays machine, production, and energy records in tables.
Keep both terminals running while using the dashboard. Stop either service
with `Ctrl+C` in its terminal.

## Project structure

```text
industrial-operations-data-platform/
├── backend/
│   ├── load_to_sqlite.py
│   ├── validate_data.py
│   ├── database.py          # SQLite connection helper
│   ├── main.py              # FastAPI application and endpoints
│   └── queries.py           # SQL queries and KPI calculations
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
