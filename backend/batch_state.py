import sqlite3
from contextlib import closing
from pathlib import Path


def _connect(project_root: Path) -> sqlite3.Connection:
    state_dir = project_root / "data_lake" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(state_dir / "processed_batches.sqlite3")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_batches (
            data_type TEXT NOT NULL,
            object_key TEXT NOT NULL,
            etag TEXT NOT NULL,
            processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (data_type, object_key, etag)
        )
        """
    )
    return connection


def is_batch_processed(
    data_type: str,
    object_key: str,
    etag: str,
    project_root: Path,
) -> bool:
    with closing(_connect(project_root)) as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM processed_batches
            WHERE data_type = ? AND object_key = ? AND etag = ?
            """,
            (data_type, object_key, etag),
        ).fetchone()
    return row is not None


def mark_batch_processed(
    data_type: str,
    object_key: str,
    etag: str,
    project_root: Path,
) -> None:
    with closing(_connect(project_root)) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO processed_batches
                (data_type, object_key, etag)
            VALUES (?, ?, ?)
            """,
            (data_type, object_key, etag),
        )
        connection.commit()
