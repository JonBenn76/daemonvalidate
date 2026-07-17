import csv
from pathlib import Path
from typing import Dict, Any, Type
from pydantic import BaseModel, ValidationError

class PostboxProcessor:
    """
    Streaming data processor that acts as a pure, zero-state filter chute.
    Streams input CSV line-by-line, validating against a Pydantic model.
    """
    
    def __init__(self, validation_model: Type[BaseModel]) -> None:
        self.model = validation_model

    def process_csv_stream(
        self, 
        input_path: Path, 
        valid_output_path: Path, 
        quarantine_output_path: Path
    ) -> Dict[str, int]:
        """
        Processes a bulk CSV file line-by-line, partitioning data into two destinations.
        
        Returns:
            Dict[str, int]: Runtime operational execution counters.
        """
        metrics = {
            "total_records": 0,
            "valid_records": 0,
            "quarantined_records": 0
        }
        
        # Open all files as streams simultaneously to ensure zero buffering footprint
        with (
            open(input_path, "r", newline="", encoding="utf-8") as infile,
            open(valid_output_path, "w", newline="", encoding="utf-8") as valid_file,
            open(quarantine_output_path, "w", newline="", encoding="utf-8") as quarantine_file
        ):
            reader = csv.DictReader(infile)
            if not reader.fieldnames:
                raise ValueError(f"The input CSV file at {input_path} is completely empty or missing headers.")
                
            # Initialize downstream writers matching the exact raw header blueprint
            valid_writer = csv.DictWriter(valid_file, fieldnames=reader.fieldnames)
            quarantine_writer = csv.DictWriter(quarantine_file, fieldnames=reader.fieldnames)
            
            valid_writer.writeheader()
            quarantine_writer.writeheader()
            
            # The streaming loop: memory usage remains flat regardless of total row count
            for row in reader:
                metrics["total_records"] += 1
                try:
                    # Pydantic attempts parsing and type coercion
                    self.model(**row)
                    
                    # Passed validation -> send to the clean staging chute
                    valid_writer.writerow(row)
                    metrics["valid_records"] += 1
                    
                except ValidationError:
                    # Failed validation -> drop raw unaltered row into the recovery bin
                    quarantine_writer.writerow(row)
                    metrics["quarantined_records"] += 1
                    
        return metrics