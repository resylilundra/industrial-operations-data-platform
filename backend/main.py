from fastapi import FastAPI
from typing import Literal
from backend.database import get_connection
from backend.queries import (
    get_all_energy_data,
    get_all_machines,
    get_all_production_data,
    get_average_temperature,
    get_defect_rate,
    get_energy_per_unit,
    get_total_output,
    get_total_downtime,
    get_machine_performance,
)

app = FastAPI(title="Industrial Operations Data Platform")


@app.get("/machines")
def read_machines() -> list[dict]:
    connection = get_connection()
    try:
        return get_all_machines(connection)
    finally:
        connection.close()


@app.get("/production")
def read_production_data() -> list[dict]:
    connection = get_connection()
    try:
        return get_all_production_data(connection)
    finally:
        connection.close()


@app.get("/energy")
def read_energy_data() -> list[dict]:
    connection = get_connection()
    try:
        return get_all_energy_data(connection)
    finally:
        connection.close()


@app.get("/kpis/total-output")
def read_total_output(
    period: Literal["all_time", "last_hour"] = "all_time",
) -> float:
    connection = get_connection()
    try:
        return get_total_output(connection, period)
    finally:
        connection.close()


@app.get("/kpis/average-temperature")
def read_average_temperature(
    period: Literal["all_time", "last_hour"] = "all_time",
) -> float | None:
    connection = get_connection()
    try:
        return get_average_temperature(connection,period)
    finally:
        connection.close()


@app.get("/kpis/defect-rate")
def read_defect_rate( period: Literal["all_time", "last_hour"] = "all_time",
) -> float | None:
    connection = get_connection()
    try:
        return get_defect_rate(connection, period)
    finally:
        connection.close()


@app.get("/kpis/energy-per-unit")
def read_energy_per_unit( period: Literal["all_time", "last_hour"] = "all_time",
) -> float | None:
    connection = get_connection()
    try:
        return get_energy_per_unit(connection ,period)
    finally:
        connection.close()


@app.get("/kpis/total-downtime")
def read_total_downtime( period: Literal["all_time", "last_hour"] = "all_time",
) -> float:
    connection = get_connection()
    try:
        return get_total_downtime(connection,period)
    finally:
        connection.close()

@app.get("/production/performance")
def read_machine_performance(
    period: Literal["all_time", "last_hour"] = "all_time",
) -> list[dict]:
    connection = get_connection()
    try:
        return get_machine_performance(connection, period)
    finally:
        connection.close()
        