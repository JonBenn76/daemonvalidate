# run_sandbox.py
import uuid
import datetime
from pathlib import Path
import duckdb
from daemonvalidate.config import DaemonConfig
from daemonvalidate.loaders import YamlSchemaLoader
from daemonvalidate.models import compile_dynamic_model
from daemonvalidate.core import PostboxProcessor
from daemonvalidate.telemetry import TelemetryLogger

def generate_mock_operational_data(file_path: Path, row_count: int = 10000):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("transaction_id,customer_id,total_revenue,quantity_ordered,is_retail_customer\n")
        for i in range(1, row_count + 1):
            if i % 250 == 0:
                f.write(f"TXN-{i:06d},CUST-{1000+i},MANGLED_REVENUE,NOT_AN_INT,true\n")
            else:
                revenue = round(15.50 * (i % 10 + 1), 2)
                quantity = (i % 5) + 1
                is_retail = "true" if i % 2 == 0 else "false"
                f.write(f"TXN-{i:06d},CUST-{1000+i},{revenue},{quantity},{is_retail}\n")

def run_simulation():
    base_dir = Path(__file__).parent
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    
    # 1. Load the central configuration architecture
    print("Loading environmental configuration rules...")
    config = DaemonConfig(base_dir / "daemon_config.yaml")
    
    # 2. Build runtime workspace paths completely driven by configuration
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    workspace_dir = config.base_run_dir / current_date / run_id
    input_csv = workspace_dir / "raw_production_feed.csv"
    
    # Generate mock production data directly inside our dynamic run workspace
    generate_mock_operational_data(input_csv, row_count=10000)
    
    # 3. Load Schema Blueprint & Compile Model
    loader = YamlSchemaLoader(str(base_dir / "sales_blueprint.yaml"))
    SalesModel = compile_dynamic_model("SalesPipelineModel", loader.load_schema())
    
    # 4. Initialize components with dynamically driven configurations
    processor = PostboxProcessor(SalesModel)
    telemetry = TelemetryLogger(config.database_path)
    
    print(f"Streaming data channel active. Deploying outputs into: {workspace_dir}")
    result = processor.process_csv_stream(
        input_path=input_csv,
        output_dir=workspace_dir,
        max_error_rate=0.05,
        valid_filename=config.valid_filename,
        quarantine_filename=config.quarantine_filename,
        diagnostics_filename=config.diagnostics_filename
    )
    
    # 5. Flush runtime metadata log down to configured DuckDB path
    telemetry.log_execution(run_id=run_id, pipeline_name="sales_edge_ingest", metrics=result["metrics"])
    
    print("\n" + "="*60)
    print("DYNAMIC OPERATION COMPLETED")
    print("="*60)
    print(f"Target Database Engine   : {config.database_path.name}")
    print(f"Structured Storage Bin   : {workspace_dir}")
    print(f"Valid Output Filename    : {Path(result['outputs']['valid_path']).name}")
    print(f"Quarantine Filename      : {Path(result['outputs']['quarantine_path']).name}")
    print(f"Diagnostics Autopsy File : {Path(result['outputs']['diagnostics_path']).name}")
    print("="*60)

    # 6. Query checking the telemetry using our configured file path
    print("\nVerifying Custom Target Audit Database Log State:")
    with duckdb.connect(str(config.database_path)) as conn:
        cursor = conn.execute("""
            SELECT 
                vm.run_id AS id,
                vm.total_record AS total,
                vm.quarantined_record AS bad
            FROM validation_metrics AS vm
            ORDER BY vm.execution_timestamp DESC
            LIMIT 1;
        """)
        db_row = cursor.fetchone()
        print(f"-> Verified Log Write in {config.database_path.name}: ID={db_row[0]} | Rows={db_row[1]} | Errors={db_row[2]}")
    print("="*60)

if __name__ == "__main__":
    run_simulation()