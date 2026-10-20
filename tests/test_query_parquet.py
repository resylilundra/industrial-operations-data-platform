import pandas as pd
import pytest

from backend.query_parquet import (
    get_parquet_kpis,
    get_average_temperature,
    get_defect_rate,
    get_energy_per_unit,
    get_total_downtime,
    get_total_output,
)


def test_get_parquet_kpis_returns_duckdb_values(tmp_path):
    production_path = tmp_path / "production.parquet"
    energy_path = tmp_path / "energy.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "output_units": [100],
            "defect_units": [2],
            "downtime_minutes": [5],
        }
    ).to_parquet(production_path, index=False)
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "temperature": [70],
            "energy_kwh": [10],
            "vibration": [0.2],
        }
    ).to_parquet(energy_path, index=False)

    result = get_parquet_kpis(str(production_path), str(energy_path))

    assert result == {
        "total_output": 100,
        "defect_rate": 2.0,
        "total_downtime": 5,
        "average_temperature": 70.0,
        "energy_per_unit": 0.1,
    }


def test_get_total_output_sums_parquet_rows(tmp_path):
    parquet_path = tmp_path / "production.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00", "2026-10-17 22:00:10"],
            "machine_id": ["M001", "M002"],
            "output_units": [100, 150],
            "defect_units": [2, 3],
            "downtime_minutes": [0, 0],
        }
    ).to_parquet(parquet_path, index=False)

    result = get_total_output(str(parquet_path))

    assert result == 250

def test_get_total_output_returns_zero_for_empty_parquet(tmp_path):
    parquet_path = tmp_path / "empty-production.parquet"

    empty_df = pd.DataFrame(
        {
            "timestamp": pd.Series(dtype="datetime64[ns]"),
            "machine_id": pd.Series(dtype="string"),
            "output_units": pd.Series(dtype="float64"),
            "defect_units": pd.Series(dtype="float64"),
            "downtime_minutes": pd.Series(dtype="float64"),
        }
    )
    empty_df.to_parquet(parquet_path, index=False)

    result = get_total_output(str(parquet_path))

    assert result == 0

def test_get_total_output_counts_identical_duplicate_once(tmp_path):
    columns = {
        "timestamp": ["2026-10-17 22:00:00"],
        "machine_id": ["M001"],
        "output_units": [100],
        "defect_units": [2],
        "downtime_minutes": [0],
    }
    pd.DataFrame(columns).to_parquet(tmp_path / "batch-one.parquet", index=False)
    pd.DataFrame(columns).to_parquet(tmp_path / "batch-two.parquet", index=False)

    result = get_total_output(str(tmp_path / "*.parquet"))

    assert result == 100

def test_get_total_output_reports_conflicting_duplicate(tmp_path):
    first = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "output_units": [100],
            "defect_units": [2],
            "downtime_minutes": [0],
        }
    )
    second = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "output_units": [120],
            "defect_units": [2],
            "downtime_minutes": [0],
        }
    )
    first.to_parquet(tmp_path / "batch-one.parquet", index=False)
    second.to_parquet(tmp_path / "batch-two.parquet", index=False)

    with pytest.raises(ValueError, match="Conflicting duplicate production readings"):
        get_total_output(str(tmp_path / "*.parquet"))
def test_get_defect_rate_calculates_percentage(tmp_path):
    parquet_path = tmp_path / "production.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00", "2026-10-17 22:00:10"],
            "machine_id": ["M001", "M002"],
            "output_units": [100, 150],
            "defect_units": [2, 3],
            "downtime_minutes": [0, 0],
        }
    ).to_parquet(parquet_path, index=False)

    result = get_defect_rate(str(parquet_path))

    # (2 + 3) defects / (100 + 150) output * 100 = 2%
    assert result == pytest.approx(2.0)

def test_get_defect_rate_returns_none_when_total_output_is_zero(tmp_path):
    parquet_path = tmp_path / "zero-output.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "output_units": [0],
            "defect_units": [0],
            "downtime_minutes": [0],
        }
    ).to_parquet(parquet_path, index=False)

    result = get_defect_rate(str(parquet_path))

    assert result is None


def test_get_defect_rate_counts_identical_duplicate_once(tmp_path):
    reading = {
        "timestamp": ["2026-10-17 22:00:00"],
        "machine_id": ["M001"],
        "output_units": [100],
        "defect_units": [2],
        "downtime_minutes": [0],
    }
    pd.DataFrame(reading).to_parquet(tmp_path / "batch-one.parquet", index=False)
    pd.DataFrame(reading).to_parquet(tmp_path / "batch-two.parquet", index=False)

    result = get_defect_rate(str(tmp_path / "*.parquet"))

    assert result == pytest.approx(2.0)
def test_get_total_downtime_sums_parquet_rows(tmp_path):
    parquet_path = tmp_path / "production.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00", "2026-10-17 22:00:10"],
            "machine_id": ["M001", "M002"],
            "output_units": [100, 150],
            "defect_units": [2, 3],
            "downtime_minutes": [5, 7],
        }
    ).to_parquet(parquet_path, index=False)

    result = get_total_downtime(str(parquet_path))

    # 5 + 7 minutes = 12 minutes
    assert result == 12


def test_get_total_downtime_returns_zero_for_empty_parquet(tmp_path):
    parquet_path = tmp_path / "empty-production.parquet"
    pd.DataFrame(
        {
            "timestamp": pd.Series(dtype="datetime64[ns]"),
            "machine_id": pd.Series(dtype="string"),
            "output_units": pd.Series(dtype="float64"),
            "defect_units": pd.Series(dtype="float64"),
            "downtime_minutes": pd.Series(dtype="float64"),
        }
    ).to_parquet(parquet_path, index=False)

    result = get_total_downtime(str(parquet_path))

    assert result == 0

def test_get_total_downtime_returns_zero_for_empty_parquet(tmp_path):
    parquet_path = tmp_path / "empty-production.parquet"
    pd.DataFrame(
        {
            "timestamp": pd.Series(dtype="datetime64[ns]"),
            "machine_id": pd.Series(dtype="string"),
            "output_units": pd.Series(dtype="float64"),
            "defect_units": pd.Series(dtype="float64"),
            "downtime_minutes": pd.Series(dtype="float64"),
        }
    ).to_parquet(parquet_path, index=False)

    result = get_total_downtime(str(parquet_path))

    assert result == 0


def test_get_total_downtime_counts_identical_duplicate_once(tmp_path):
    reading = {
        "timestamp": ["2026-10-17 22:00:00"],
        "machine_id": ["M001"],
        "output_units": [100],
        "defect_units": [2],
        "downtime_minutes": [5],
    }
    pd.DataFrame(reading).to_parquet(tmp_path / "batch-one.parquet", index=False)
    pd.DataFrame(reading).to_parquet(tmp_path / "batch-two.parquet", index=False)

    result = get_total_downtime(str(tmp_path / "*.parquet"))

    assert result == 5


def test_get_average_temperature_calculates_mean(tmp_path):
    parquet_path = tmp_path / "energy.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00", "2026-10-17 22:00:10"],
            "machine_id": ["M001", "M002"],
            "temperature": [70, 80],
            "energy_kwh": [10, 12],
            "vibration": [0.2, 0.3],
        }
    ).to_parquet(parquet_path, index=False)

    result = get_average_temperature(str(parquet_path))

    assert result == pytest.approx(75)


def test_get_average_temperature_returns_none_for_empty_parquet(tmp_path):
    parquet_path = tmp_path / "empty-energy.parquet"
    pd.DataFrame(
        {
            "timestamp": pd.Series(dtype="datetime64[ns]"),
            "machine_id": pd.Series(dtype="string"),
            "temperature": pd.Series(dtype="float64"),
            "energy_kwh": pd.Series(dtype="float64"),
            "vibration": pd.Series(dtype="float64"),
        }
    ).to_parquet(parquet_path, index=False)

    result = get_average_temperature(str(parquet_path))

    assert result is None


def test_get_average_temperature_counts_identical_duplicate_once(tmp_path):
    first = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "temperature": [70],
            "energy_kwh": [10],
            "vibration": [0.2],
        }
    )
    second = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:10"],
            "machine_id": ["M002"],
            "temperature": [80],
            "energy_kwh": [12],
            "vibration": [0.3],
        }
    )
    first.to_parquet(tmp_path / "batch-one.parquet", index=False)
    first.to_parquet(tmp_path / "batch-two.parquet", index=False)
    second.to_parquet(tmp_path / "batch-three.parquet", index=False)

    result = get_average_temperature(str(tmp_path / "*.parquet"))

    assert result == pytest.approx(75)


def test_get_average_temperature_reports_conflicting_duplicate(tmp_path):
    first = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "temperature": [70],
            "energy_kwh": [10],
            "vibration": [0.2],
        }
    )
    second = first.copy()
    second.loc[0, "temperature"] = 72
    first.to_parquet(tmp_path / "batch-one.parquet", index=False)
    second.to_parquet(tmp_path / "batch-two.parquet", index=False)

    with pytest.raises(ValueError, match="Conflicting duplicate energy readings"):
        get_average_temperature(str(tmp_path / "*.parquet"))


def test_get_energy_per_unit_calculates_ratio(tmp_path):
    production_path = tmp_path / "production.parquet"
    energy_path = tmp_path / "energy.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00", "2026-10-17 22:00:10"],
            "machine_id": ["M001", "M002"],
            "output_units": [100, 200],
            "defect_units": [2, 3],
            "downtime_minutes": [0, 5],
        }
    ).to_parquet(production_path, index=False)
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00", "2026-10-17 22:00:10"],
            "machine_id": ["M001", "M002"],
            "temperature": [70, 80],
            "energy_kwh": [10, 20],
            "vibration": [0.2, 0.3],
        }
    ).to_parquet(energy_path, index=False)

    result = get_energy_per_unit(
        str(production_path),
        str(energy_path),
    )

    # (10 + 20) kWh / (100 + 200) output units = 0.1 kWh per unit
    assert result == pytest.approx(0.1)


def test_get_energy_per_unit_returns_none_when_output_is_zero(tmp_path):
    production_path = tmp_path / "zero-production.parquet"
    energy_path = tmp_path / "energy.parquet"
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "output_units": [0],
            "defect_units": [0],
            "downtime_minutes": [0],
        }
    ).to_parquet(production_path, index=False)
    pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "temperature": [70],
            "energy_kwh": [10],
            "vibration": [0.2],
        }
    ).to_parquet(energy_path, index=False)

    result = get_energy_per_unit(
        str(production_path),
        str(energy_path),
    )

    assert result is None


def test_get_energy_per_unit_counts_identical_duplicates_once(tmp_path):
    production = {
        "timestamp": ["2026-10-17 22:00:00"],
        "machine_id": ["M001"],
        "output_units": [100],
        "defect_units": [2],
        "downtime_minutes": [0],
    }
    energy = {
        "timestamp": ["2026-10-17 22:00:00"],
        "machine_id": ["M001"],
        "temperature": [70],
        "energy_kwh": [10],
        "vibration": [0.2],
    }
    pd.DataFrame(production).to_parquet(
        tmp_path / "production-one.parquet",
        index=False,
    )
    pd.DataFrame(production).to_parquet(
        tmp_path / "production-two.parquet",
        index=False,
    )
    pd.DataFrame(energy).to_parquet(
        tmp_path / "energy-one.parquet",
        index=False,
    )
    pd.DataFrame(energy).to_parquet(
        tmp_path / "energy-two.parquet",
        index=False,
    )

    result = get_energy_per_unit(
        str(tmp_path / "production-*.parquet"),
        str(tmp_path / "energy-*.parquet"),
    )

    assert result == pytest.approx(0.1)


def test_get_energy_per_unit_reports_conflicting_duplicate_energy(tmp_path):
    production = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "output_units": [100],
            "defect_units": [2],
            "downtime_minutes": [0],
        }
    )
    energy = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "temperature": [70],
            "energy_kwh": [10],
            "vibration": [0.2],
        }
    )
    conflicting_energy = energy.copy()
    conflicting_energy.loc[0, "energy_kwh"] = 12

    production.to_parquet(tmp_path / "production.parquet", index=False)
    energy.to_parquet(tmp_path / "energy-one.parquet", index=False)
    conflicting_energy.to_parquet(tmp_path / "energy-two.parquet", index=False)

    with pytest.raises(ValueError, match="Conflicting duplicate energy readings"):
        get_energy_per_unit(
            str(tmp_path / "production.parquet"),
            str(tmp_path / "energy-*.parquet"),
        )


def test_get_energy_per_unit_reports_conflicting_duplicate_production(tmp_path):
    production = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "output_units": [100],
            "defect_units": [2],
            "downtime_minutes": [0],
        }
    )
    conflicting_production = production.copy()
    conflicting_production.loc[0, "output_units"] = 120
    energy = pd.DataFrame(
        {
            "timestamp": ["2026-10-17 22:00:00"],
            "machine_id": ["M001"],
            "temperature": [70],
            "energy_kwh": [10],
            "vibration": [0.2],
        }
    )

    production.to_parquet(tmp_path / "production-one.parquet", index=False)
    conflicting_production.to_parquet(
        tmp_path / "production-two.parquet",
        index=False,
    )
    energy.to_parquet(tmp_path / "energy.parquet", index=False)

    with pytest.raises(
        ValueError,
        match="Conflicting duplicate production readings",
    ):
        get_energy_per_unit(
            str(tmp_path / "production-*.parquet"),
            str(tmp_path / "energy.parquet"),
        )
