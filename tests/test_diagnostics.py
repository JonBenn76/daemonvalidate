import pytest
import json
from pathlib import Path
from daemonvalidate.models import compile_dynamic_model
from daemonvalidate.core import PostboxProcessor, CircuitBreakerError

def test_diagnostics_autopsy_generation(tmp_path: Path):
    schema = {"fields": {"item_id": "string", "price": "float"}}
    TestModel = compile_dynamic_model("DiagModel", schema)
    processor = PostboxProcessor(TestModel)
    
    input_csv = tmp_path / "input.csv"
    input_csv.write_text("item_id,price\nITEM-01,BAD_PRICE\n")
    
    valid_out = tmp_path / "valid.csv"
    quarantine_out = tmp_path / "quarantine.csv"
    diag_out = tmp_path / "diagnostics.jsonl"
    
    processor.process_csv_stream(input_csv, valid_out, quarantine_out, diag_out)
    
    # Read and parse JSONL stream
    diag_lines = diag_out.read_text().splitlines()
    assert len(diag_lines) == 1
    
    autopsy = json.loads(diag_lines[0])
    assert autopsy["row_index"] == 1
    assert autopsy["raw_data"]["price"] == "BAD_PRICE"
    assert autopsy["errors"][0]["field"] == "price"
    assert "Input should be a valid number" in autopsy["errors"][0]["message"]


def test_circuit_breaker_trips(tmp_path: Path):
    schema = {"fields": {"count": "integer"}}
    TestModel = compile_dynamic_model("CircuitModel", schema)
    processor = PostboxProcessor(TestModel)
    
    input_csv = tmp_path / "input.csv"
    # 3 out of 4 fields are garbage (75% failure rate)
    input_csv.write_text("count\nBAD\nBAD\nBAD\n10\n")
    
    valid_out = tmp_path / "valid.csv"
    quarantine_out = tmp_path / "quarantine.csv"
    diag_out = tmp_path / "diagnostics.jsonl"
    
    # Enforce a max 20% error rate threshold
    with pytest.raises(CircuitBreakerError) as exc_info:
        processor.process_csv_stream(
            input_csv, valid_out, quarantine_out, diag_out, max_error_rate=0.20
        )
        
    assert "Catastrophic failure threshold breached" in str(exc_info.value)