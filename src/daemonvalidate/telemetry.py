import datetime
from pathlib import Path
import duckdb

class TelemetryLogger:
    """Handles operational logging of processing metrics into a central analytical DuckDB file."""
    
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initializes the metrics log table using strict lower_snake_case and plural names."""
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_metrics (
                    run_id VARCHAR PRIMARY KEY,
                    pipeline_name VARCHAR,
                    execution_timestamp TIMESTAMP,
                    total_record INTEGER,
                    valid_record INTEGER,
                    quarantined_record INTEGER
                );
            """)

    def log_execution(
        self, 
        run_id: str, 
        pipeline_name: str, 
        metrics: dict[str, int]
    ) -> None:
        """Inserts an execution run summary directly into the analytical metadata layer."""
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO validation_metrics (
                    run_id, 
                    pipeline_name, 
                    execution_timestamp, 
                    total_record, 
                    valid_record, 
                    quarantined_record
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    run_id,
                    pipeline_name,
                    datetime.datetime.now(datetime.timezone.utc),
                    metrics["total_records"],
                    metrics["valid_records"],
                    metrics["quarantined_records"]
                )
            )