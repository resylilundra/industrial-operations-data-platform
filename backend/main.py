from fastapi import FastAPI

from backend.database import get_connection
from backend.queries import (
    get_all_energy_data,
    get_all_machines,
    get_all_production_data,
    get_average_temperature,
    get_total_output,
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
def read_total_output() -> float:
    connection = get_connection()
    try:
        return get_total_output(connection)
    finally:
        connection.close()


@app.get("/kpis/average-temperature")
def read_average_temperature() -> float | None:
    connection = get_connection()
    try:
        return get_average_temperature(connection)
    finally:
        connection.close()