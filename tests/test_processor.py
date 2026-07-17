import pytest
from pathlib import Path
from daemonvalidate.models import compile_dynamic_model
from daemonvalidate.core import PostboxProcessor

def test_streaming_split_stream_routing(tmp_path: Path):
    # 1. Arrange: Compile a standard testing model blueprint
    schema = {
        "fields": {
            "item_id": "string",
            "price": "float",
            "quantity": "integer"
        }
    }
    TestModel = compile_dynamic_model("TestModel", schema)
    processor = PostboxProcessor(TestModel)
    
    # 2. Arrange: Set up sample data with intentional anomalies
    input_csv = tmp_path / "raw_api_payload.csv"
    input_csv.write_text(
        "item_id,price,quantity\n"
        "ITEM-01,19.99,5\n"      # Clean record
        "ITEM-02,BAD_PRICE,2\n"  # Faulty price (fails validation)
        "ITEM-03,4.50,NOT_INT\n" # Faulty quantity (fails validation)
        "ITEM-04,100.00,10\n"    # Clean record
    )
    
    valid_out = tmp_path / "valid_records.csv"
    quarantine_out = tmp_path / "quarantine_records.csv"
    diag_out = tmp_path / "diagnostics.jsonl"  # Added for Milestone 3 compatibility
    
    # 3. Act: Execute the split-stream filter loop
    metrics = processor.process_csv_stream(input_csv, valid_out, quarantine_out, diag_out)
    
    # 4. Assert: Structural telemetry assertions
    assert metrics["total_records"] == 4
    assert metrics["valid_records"] == 2
    assert metrics["quarantined_records"] == 2
    
    # 5. Assert: Verify structural segregation in output streams
    valid_content = valid_out.read_text().splitlines()
    assert len(valid_content) == 3 # Header + 2 rows
    assert "ITEM-01" in valid_content[1]
    assert "ITEM-04" in valid_content[2]
    
    quarantine_content = quarantine_out.read_text().splitlines()
    assert len(quarantine_content) == 3 # Header + 2 rows
    assert "ITEM-02" in quarantine_content[1]
    assert "ITEM-03" in quarantine_content[2]