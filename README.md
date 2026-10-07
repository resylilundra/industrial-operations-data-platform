# Industrial Operations Data Platform

A small data platform prototype for monitoring industrial operations.

It combines static company data, such as sites and machines, with dynamic
operational data, such as production output, downtime, temperature, energy
consumption, and vibration.

The goal is to build a simple backend API and dashboard for visualizing
operational KPIs.

## Features

- Load CSV data with Pandas
- Validate missing values and data relationships
- Store validated data in SQLite
- Provide API endpoints with FastAPI
- Display production, downtime, energy, and machine KPIs in Streamlit
- Create interactive Plotly visualizations

## Technologies

- Python
- Pandas
- FastAPI
- Streamlit
- SQLite
- Plotly

## Project Structure

```text
industrial-operations-data-platform/
├── data/          # Source CSV files and generated SQLite database
├── backend/       # Data loading, validation, database, and API code
├── dashboard/     # Streamlit dashboard code
├── images/        # Project screenshots and visuals
├── requirements.txt
└── README.md
```

## Setup

1. Clone the repository and enter the project directory:

   ```bash
   git clone <your-repository-url>
   cd industrial-operations-data-platform
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   ```

   On macOS or Linux:

   ```bash
   source venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```
