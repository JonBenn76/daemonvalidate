import pytest
from pathlib import Path
import duckdb
from daemonvalidate.telemetry import TelemetryLogger

def test_telemetry_duckdb_logging(tmp_path: Path):
    db_file = tmp_path / "daemonflow.duckdb"
    logger = TelemetryLogger(db_file)
    
    mock_metrics = {
        "total_records": 1000,
        "valid_records": 950,
        "quarantined_records": 50
    }
    
    # 1. Act: Log a mock processing execution run
    logger.log_execution(
        run_id="run-abc-123",
        pipeline_name="sales_ingestion",
        metrics=mock_metrics
    )
    
    # 2. Assert: Open a completely clean connection to verify persistent table writes
    with duckdb.connect(str(db_file)) as conn:
        # Enforcing our coding standard guidelines: explicit column selection using uppercase AS aliases
        cursor = conn.execute("""
            SELECT 
                vm.pipeline_name AS pipeline,
                vm.total_record AS total,
                vm.quarantined_record AS quarantined
            FROM validation_metrics AS vm
            WHERE vm.run_id = 'run-abc-123';
        """)
        row = cursor.fetchone()
        
    assert row is not None
    assert row[0] == "sales_ingestion"
    assert row[1] == 1000
    assert row[2] == 50