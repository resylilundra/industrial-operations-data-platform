## Data Quality and Validation Policy

Raw source CSV files are kept unchanged. Data cleaning and validation happen in the ingestion pipeline.

### Automatic corrections

The following issues are corrected automatically because they are formatting inconsistencies:

- Leading and trailing whitespace is removed from text fields.
- IDs are converted to uppercase where applicable.
- Column names are normalized to lowercase snake_case.
- Known site-ID formatting mistakes are corrected when the intended value is unambiguous.
  - Example: `SO01` is corrected to `S001` because site IDs use the format `S` followed by three digits.

All automatic corrections should be logged.

### Rejected rows

Rows are rejected and saved for review when they contain:

- Missing required identifiers, such as `site_id` or `machine_id`
- Duplicate primary keys
- Invalid foreign keys
  - Example: a machine referencing a site that does not exist in `sites.csv`
- Invalid numeric values
  - Example: negative production quantity, negative energy usage, or defect quantity greater than total production
- Invalid dates or timestamps
- Required fields that remain invalid after safe formatting corrections

Rejected rows are not silently deleted. They are stored with a rejection reason for inspection.

### Known source-data issues

| File | Issue | Decision |
| :--- | :--- | :--- |
| `machines.csv` | Duplicate machine ID `M003` | Reject the duplicate row unless a defined business rule identifies an authoritative record |
| `machines.csv` | Site ID `SO01` instead of `S001` | Correct automatically and log the correction |
| Source CSV files | Whitespace and spelling inconsistencies | Trim whitespace; correct only explicitly defined, unambiguous spelling variations |


### Energy data

- `temperature` is required, numeric, and must be between 0 and 200.
- `energy_kwh` must be numeric and non-negative.
- `vibration` must be numeric and non-negative.
- Every `machine_id` must reference an accepted machine.
- Each `machine_id` and `timestamp` combination must be unique.
