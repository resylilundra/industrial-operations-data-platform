import requests
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8000"


def fetch_api_data(endpoint):
    """Request JSON data from the API and show an error if it fails."""
    try:
        response = requests.get(
            f"{API_BASE_URL}{endpoint}",
            timeout=5,
        )
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as error:
        st.error(f"Could not load {endpoint}: {error}")
        return False, None


st.title("Industrial Operations Dashboard")
st.write("Production, machine, and energy information from the operations database.")

machines_ok, machines = fetch_api_data("/machines")
production_ok, production = fetch_api_data("/production")
energy_ok, energy = fetch_api_data("/energy")
total_output_ok, total_output = fetch_api_data("/kpis/total-output")
average_temperature_ok, average_temperature = fetch_api_data(
    "/kpis/average-temperature"
)


st.header("Key performance indicators")

column1, column2 = st.columns(2)

with column1:
    if total_output_ok:
        st.metric("Total output", f"{total_output:,.2f}")

with column2:
    if average_temperature_ok:
        if average_temperature is None:
            st.metric("Average temperature", "No data")
        else:
            st.metric("Average temperature", f"{average_temperature:.1f}")


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