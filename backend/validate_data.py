from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REJECTED_DIR = PROJECT_ROOT / "data" / "rejected"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

for folder in [PROCESSED_DIR, REJECTED_DIR, REPORTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


def normalize_column_name(column_name: str) -> str:
    """Convert source column names to lowercase snake_case."""
    return (
        str(column_name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def normalize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Apply only documented, safe corrections:
    - normalize column names
    - trim whitespace from text fields
    - correct known site-ID typo: SO01 -> S001
    """
    df = df.copy()
    corrections = []

    original_columns = list(df.columns)
    df.columns = [normalize_column_name(column) for column in df.columns]

    for original, normalized in zip(original_columns, df.columns):
        if original != normalized:
            corrections.append(
                f"Normalized column name '{original}' to '{normalized}'."
            )

    # Trim whitespace in text columns.
    for column in df.select_dtypes(include=["object", "string"]).columns:
        before = df[column].copy()

        df[column] = df[column].astype("string").str.strip()

        changed_count = (
            before.astype("string") != df[column].astype("string")
        ).sum()

        if changed_count > 0:
            corrections.append(
                f"Trimmed whitespace in '{column}' for {changed_count} row(s)."
            )
    # Standardize identifier casing.
    for column in ["site_id", "machine_id"]:
        if column in df.columns:
            before = df[column].copy()

            df[column] = df[column].astype("string").str.upper()

            changed_count = (
                before.astype("string") != df[column].astype("string")
            ).sum()

            if changed_count > 0:
                corrections.append(
                    f"Converted values in '{column}' to uppercase "
                    f"for {changed_count} row(s)."
                )

    # Documented correction from the data-quality policy.
    if "site_id" in df.columns:
        typo_mask = df["site_id"] == "SO01"
        typo_count = typo_mask.sum()

        if typo_count > 0:
            df.loc[typo_mask, "site_id"] = "S001"
            corrections.append(
                f"Corrected site_id 'SO01' to 'S001' for {typo_count} row(s)."
            )

    return df, corrections


def add_reason(df: pd.DataFrame, mask: pd.Series, reason: str) -> None:
    """Add a rejection reason while retaining any earlier reason."""
    existing = df.loc[mask, "rejection_reason"].fillna("")

    df.loc[mask, "rejection_reason"] = existing.map(
        lambda current: f"{current}; {reason}" if current else reason
    )


def initialise_validation(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    """Check the expected schema and prepare the rejection_reason field."""
    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required column(s): {', '.join(missing_columns)}"
        )

    df = df.copy()
    df["rejection_reason"] = ""

    for column in required_columns:
        missing_value_mask = (
            df[column].isna()
            | df[column].astype("string").str.strip().eq("")
        )

        add_reason(
            df,
            missing_value_mask,
            f"Missing required value: {column}",
        )

    return df


def split_valid_and_rejected(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate accepted rows from rejected rows."""
    rejected_df = df[df["rejection_reason"] != ""].copy()
    valid_df = df[df["rejection_reason"] == ""].copy()

    valid_df = valid_df.drop(columns=["rejection_reason"])

    return valid_df, rejected_df


def validate_sites(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Sites are validated first because all other data depends on them.
    """
    df, corrections = normalize_dataframe(raw_df)

    df = initialise_validation(
        df,
        required_columns=["site_id"],
    )

    duplicate_site_mask = df.duplicated(subset=["site_id"], keep=False)

    add_reason(
        df,
        duplicate_site_mask,
        "Duplicate site_id.",
    )

    valid_df, rejected_df = split_valid_and_rejected(df)

    return valid_df, rejected_df, corrections


def validate_machines(
    raw_df: pd.DataFrame,
    accepted_site_ids: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Machines must have a unique machine_id and reference an accepted site.
    """
    df, corrections = normalize_dataframe(raw_df)

    df = initialise_validation(
        df,
        required_columns=["machine_id", "site_id"],
    )

    duplicate_machine_mask = df.duplicated(subset=["machine_id"], keep=False)

    add_reason(
        df,
        duplicate_machine_mask,
        "Duplicate machine_id.",
    )

    invalid_site_mask = ~df["site_id"].isin(accepted_site_ids)

    add_reason(
        df,
        invalid_site_mask,
        "Invalid site_id: not found in accepted sites.",
    )

    valid_df, rejected_df = split_valid_and_rejected(df)

    return valid_df, rejected_df, corrections


def validate_production_data(
    raw_df: pd.DataFrame,
    accepted_machine_ids: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Production records must reference accepted machines and contain valid
    timestamps and non-negative production values.
    """
    df, corrections = normalize_dataframe(raw_df)

    required_columns = [
        "timestamp",
        "machine_id",
        "output_units",
        "defect_units",
        "downtime_minutes",
    ]

    df = initialise_validation(df, required_columns)

    # Convert timestamp. Invalid values become NaT.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    add_reason(
        df,
        df["timestamp"].isna(),
        "Invalid timestamp.",
    )

    # Convert numerical fields. Invalid values become NaN.
    numeric_columns = [
        "output_units",
        "defect_units",
        "downtime_minutes",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

        add_reason(
            df,
            df[column].isna(),
            f"Invalid numeric value: {column}.",
        )

    # Reject impossible negative values.
    add_reason(
        df,
        df["output_units"] < 0,
        "output_units cannot be negative.",
    )

    add_reason(
        df,
        df["defect_units"] < 0,
        "defect_units cannot be negative.",
    )

    add_reason(
        df,
        df["downtime_minutes"] < 0,
        "downtime_minutes cannot be negative.",
    )

    # Defective units cannot exceed the total output.
    add_reason(
        df,
        df["defect_units"] > df["output_units"],
        "defect_units cannot exceed output_units.",
    )

    # The machine must exist in the accepted machines dataset.
    add_reason(
        df,
        ~df["machine_id"].isin(accepted_machine_ids),
        "Invalid machine_id: not found in accepted machines.",
    )

    # One production row per machine and timestamp.
    duplicate_mask = df.duplicated(
        subset=["timestamp", "machine_id"],
        keep=False,
    )

    add_reason(
        df,
        duplicate_mask,
        "Duplicate timestamp and machine_id combination.",
    )

    valid_df, rejected_df = split_valid_and_rejected(df)

    return valid_df, rejected_df, corrections


def validate_energy_data(
    raw_df: pd.DataFrame,
    accepted_machine_ids: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Energy records must reference accepted machines and contain valid
    sensor/energy readings.
    """
    df, corrections = normalize_dataframe(raw_df)

    required_columns = [
        "timestamp",
        "machine_id",
        "temperature",
        "energy_kwh",
        "vibration",
    ]

    df = initialise_validation(df, required_columns)

    # Convert timestamp.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    add_reason(
        df,
        df["timestamp"].isna(),
        "Invalid timestamp.",
    )

    # Convert numerical fields.
    numeric_columns = [
        "temperature",
        "energy_kwh",
        "vibration",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

        add_reason(
            df,
            df[column].isna(),
            f"Invalid numeric value: {column}.",
        )

    # Temperature must remain within the documented plausible range.
    add_reason(
        df,
        (df["temperature"] < 0) | (df["temperature"] > 200),
        "temperature must be between 0 and 200.",
    )

    # Energy use and vibration cannot logically be negative.
    add_reason(
        df,
        df["energy_kwh"] < 0,
        "energy_kwh cannot be negative.",
    )

    add_reason(
        df,
        df["vibration"] < 0,
        "vibration cannot be negative.",
    )

    # Foreign-key validation against accepted machines.
    add_reason(
        df,
        ~df["machine_id"].isin(accepted_machine_ids),
        "Invalid machine_id: not found in accepted machines.",
    )

    # One sensor/energy reading per machine and timestamp.
    duplicate_mask = df.duplicated(
        subset=["timestamp", "machine_id"],
        keep=False,
    )

    add_reason(
        df,
        duplicate_mask,
        "Duplicate timestamp and machine_id combination.",
    )

    valid_df, rejected_df = split_valid_and_rejected(df)

    return valid_df, rejected_df, corrections


def save_validation_results(
    dataset_name: str,
    raw_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    corrections: list[str],
) -> dict:
    """Write clean and rejected CSVs, then return summary information."""
    processed_path = PROCESSED_DIR / f"{dataset_name}_clean.csv"
    rejected_path = REJECTED_DIR / f"{dataset_name}_rejected.csv"

    valid_df.to_csv(processed_path, index=False)
    rejected_df.to_csv(rejected_path, index=False)

    return {
        "rows_received": len(raw_df),
        "rows_accepted": len(valid_df),
        "rows_rejected": len(rejected_df),
        "corrections_applied": corrections,
    }


def main() -> None:
    # 1. Read raw immutable CSV data.
    sites_raw = pd.read_csv(RAW_DIR / "sites.csv")
    machines_raw = pd.read_csv(RAW_DIR / "machines.csv")
    production_raw = pd.read_csv(RAW_DIR / "production_data.csv")
    energy_raw = pd.read_csv(RAW_DIR / "energy_data.csv")

    # 2. Validate sites.
    sites_valid, sites_rejected, sites_corrections = validate_sites(sites_raw)

    # 3. Validate machines against accepted sites.
    accepted_site_ids = set(sites_valid["site_id"].astype(str))

    machines_valid, machines_rejected, machines_corrections = validate_machines(
        machines_raw,
        accepted_site_ids,
    )

    # 4. Validate operational data against accepted machines.
    accepted_machine_ids = set(machines_valid["machine_id"].astype(str))

    production_valid, production_rejected, production_corrections = (
        validate_production_data(
            production_raw,
            accepted_machine_ids,
        )
    )

    energy_valid, energy_rejected, energy_corrections = validate_energy_data(
        energy_raw,
        accepted_machine_ids,
    )

    # 5. Save outputs and create the quality report.
    summary = {
        "sites": save_validation_results(
            "sites",
            sites_raw,
            sites_valid,
            sites_rejected,
            sites_corrections,
        ),
        "machines": save_validation_results(
            "machines",
            machines_raw,
            machines_valid,
            machines_rejected,
            machines_corrections,
        ),
        "production_data": save_validation_results(
            "production_data",
            production_raw,
            production_valid,
            production_rejected,
            production_corrections,
        ),
        "energy_data": save_validation_results(
            "energy_data",
            energy_raw,
            energy_valid,
            energy_rejected,
            energy_corrections,
        ),
    }

    summary_path = REPORTS_DIR / "validation_summary.json"

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("\nValidation complete:\n")

    for dataset_name, result in summary.items():
        print(
            f"{dataset_name}: "
            f"{result['rows_received']} received, "
            f"{result['rows_accepted']} accepted, "
            f"{result['rows_rejected']} rejected"
        )

    print(f"\nSummary report: {summary_path}")


if __name__ == "__main__":
    main()
