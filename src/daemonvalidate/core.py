import csv
import json
from pathlib import Path
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel, ValidationError

class CircuitBreakerError(Exception):
    """Raised when the quarantined record rate exceeds the maximum tolerated threshold."""
    pass


class PostboxProcessor:
    """
    Streaming data processor that acts as a pure, zero-state filter chute.
    Streams input CSV line-by-line, validating against a Pydantic model.
    Generates JSON diagnostics for failed rows and enforces error-rate thresholds.
    """
    
    def __init__(self, validation_model: Type[BaseModel]) -> None:
        self.model = validation_model

    def process_csv_stream(
        self, 
        input_path: Path, 
        valid_output_path: Path, 
        quarantine_output_path: Path,
        diagnostics_output_path: Path,
        max_error_rate: Optional[float] = None
    ) -> Dict[str, int]:
        """
        Processes a bulk CSV file line-by-line, partitioning data into two destinations,
        writing an autopsy log for failures, and monitoring for catastrophic threshold breaches.
        
        Args:
            max_error_rate: A float between 0.0 and 1.0 (e.g., 0.10 for 10%). If exceeded, 
                            aborts processing immediately.
                            
        Returns:
            Dict[str, int]: Runtime operational execution counters.
        """
        metrics = {
            "total_records": 0,
            "valid_records": 0,
            "quarantined_records": 0
        }
        
        with (
            open(input_path, "r", newline="", encoding="utf-8") as infile,
            open(valid_output_path, "w", newline="", encoding="utf-8") as valid_file,
            open(quarantine_output_path, "w", newline="", encoding="utf-8") as quarantine_file,
            open(diagnostics_output_path, "w", encoding="utf-8") as diag_file
        ):
            reader = csv.DictReader(infile)
            if not reader.fieldnames:
                raise ValueError(f"The input CSV file at {input_path} is completely empty or missing headers.")
                
            valid_writer = csv.DictWriter(valid_file, fieldnames=reader.fieldnames)
            quarantine_writer = csv.DictWriter(quarantine_file, fieldnames=reader.fieldnames)
            
            valid_writer.writeheader()
            quarantine_writer.writeheader()
            
            for row_idx, row in enumerate(reader, start=1):
                metrics["total_records"] += 1
                try:
                    self.model(**row)
                    valid_writer.writerow(row)
                    metrics["valid_records"] += 1
                    
                except ValidationError as e:
                    quarantine_writer.writerow(row)
                    metrics["quarantined_records"] += 1
                    
                    # Construct structural autopsy entry for DaemonSteward remediation
                    autopsy = {
                        "row_index": row_idx,
                        "raw_data": row,
                        "errors": [
                            {
                                "field": "->".join(str(loc) for loc in err["loc"]),
                                "message": err["msg"],
                                "type": err["type"]
                            }
                            for err in e.errors()
                        ]
                    }
                    diag_file.write(json.dumps(autopsy) + "\n")
                    
                    # Evaluate Circuit Breaker Threshold
                    if max_error_rate is not None and metrics["total_records"] > 0:
                        current_error_rate = metrics["quarantined_records"] / metrics["total_records"]
                        if current_error_rate > max_error_rate:
                            raise CircuitBreakerError(
                                f"Catastrophic failure threshold breached. Current error rate is "
                                f"{current_error_rate:.2%}, which exceeds the max tolerated limit of {max_error_rate:.2%}."
                            )
                    
        return metrics