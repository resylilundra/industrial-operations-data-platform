import requests
import streamlit as st
import pandas as pd
import plotly.express as px

API_BASE_URL = "http://127.0.0.1:8000"


def fetch_api_data(endpoint, params=None):
    """Request JSON data from the API and show an error if it fails."""
    try:
        response = requests.get(
            f"{API_BASE_URL}{endpoint}",
            params=params,
            timeout=5,
        )
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as error:
        st.error(f"Could not load {endpoint}: {error}")
        return False, None


st.title("Industrial Operations Dashboard")
st.write("Production, machine, and energy information from the operations database.")


@st.fragment(run_every="10s")
def dashboard_content():
    period_label = st.selectbox("KPI period", ["All time", "Last hour"])
    period = "all_time" if period_label == "All time" else "last_hour"

    machines_ok, machines = fetch_api_data("/machines")
    production_ok, production = fetch_api_data("/production")
    energy_ok, energy = fetch_api_data("/energy")
    total_output_ok, total_output = fetch_api_data("/kpis/total-output",params={"period": period})
    average_temperature_ok, average_temperature = fetch_api_data(
        "/kpis/average-temperature",params={"period": period}
    )
    defect_rate_ok, defect_rate = fetch_api_data("/kpis/defect-rate",params={"period": period})
    energy_per_unit_ok, energy_per_unit = fetch_api_data("/kpis/energy-per-unit",params={"period": period})
    total_downtime_ok, total_downtime = fetch_api_data("/kpis/total-downtime",params={"period": period})
    performance_ok, performance = fetch_api_data(
    "/production/performance",
    params={"period": period},
    )
    st.caption("Dashboard data refreshes every 10 seconds.")
    st.header("Key performance indicators")

    columns = st.columns(5)

    with columns[0]:
        if total_output_ok:
            st.metric("Total output", f"{total_output:,.2f}")

    with columns[1]:
        if average_temperature_ok:
            if average_temperature is None:
                st.metric("Average temperature", "No data")
            else:
                st.metric("Average temperature", f"{average_temperature:.1f}")

    with columns[2]:
        if defect_rate_ok:
            if defect_rate is None:
                st.metric("Defect rate", "No data")
            else:
                st.metric("Defect rate", f"{defect_rate:.2f}%")

    with columns[3]:
        if energy_per_unit_ok:
            if energy_per_unit is None:
                st.metric("Energy per unit", "No data")
            else:
                st.metric("Energy per unit", f"{energy_per_unit:.3f} kWh")

    with columns[4]:
        if total_downtime_ok:
            st.metric("Total downtime", f"{total_downtime:,.0f} min")

    st.header("Machine performance over time")

    if performance_ok and performance:
        performance_df = pd.DataFrame(performance)

        output_chart = px.line(
            performance_df,
            x="timestamp",
            y="output_units",
            color="machine_id",
            markers=True,
            title="Output by machine",
        )
        st.plotly_chart(output_chart, width="stretch")

        defect_chart = px.line(
            performance_df,
            x="timestamp",
            y="defect_rate_percent",
            color="machine_id",
            markers=True,
            title="Defect rate by machine",
        )
        st.plotly_chart(defect_chart, width="stretch")
    elif performance_ok:
        st.info("There are no production readings for this period.")

    st.header("Machines")
    if machines_ok:
        if machines:
            st.dataframe(machines, use_container_width=True)
        else:
            st.info("There are no machine records to display.")

    st.header("Production records")
    if production_ok:
        if production:
            st.dataframe(production, use_container_width=True)
        else:
            st.info("There are no production records to display.")

    st.header("Energy records")
    if energy_ok:
        if energy:
            st.dataframe(energy, use_container_width=True)
        else:
            st.info("There are no energy records to display.")


dashboard_content()