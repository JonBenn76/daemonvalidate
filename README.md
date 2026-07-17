# DaemonValidate

A high-performance, zero-buffering data validation engine built for the **Daemon Suite**. DaemonValidate streams multi-gigabyte CSV feeds line-by-line using a runtime-compiled Pydantic factory, enforcing structural integrity with a flat memory footprint and isolating anomalies into dedicated operational processing bins.

---

## 🧬 Architectural Overview

1. **Blueprint Factory:** Loads data definitions from local files (YAML/JSON) or active relational schemas via `psycopg`.
2. **Dynamic Compiler:** Generates memory-efficient Pydantic validation models at runtime based on the active blueprint.
3. **Split-Stream Chute:** Utilises Python's native `csv.DictReader` to stream data iteratively, guaranteeing flat memory allocation ($O(1)$ complexity) regardless of file size.
4. **Circuit Breaker:** Real-time error rate tracking (`max_error_rate`) that aborts execution instantly if an incoming feed is fundamentally corrupted.
5. **Telemetry Layer:** Automatically logs execution summaries into a persistent DuckDB analytical warehouse using a standardised SQL architecture.

---

## ⚙️ Global Configuration (`daemon_config.yaml`)

System-wide parameters, storage targets, and database locations are managed via `daemon_config.yaml` sitting in your project root. 

```yaml
database:
  # Path to the central operational telemetry warehouse
  path: "production_audit_warehouse.duckdb"

storage:
  # Base directory where individual pipeline run metrics are isolated
  base_run_dir: "data_staging/runs"
  valid_filename: "passed_records_clean.csv"
  quarantine_filename: "quarantine_failed_records.csv"
  diagnostics_filename: "structural_autopsy_log.jsonl"
```

## Pipeline Blueprints (Field Definitions)

DaemonValidate supports **zero-configuration data ingestion** by dynamically compiling validation models from external blueprint files or live database schemas. Field attributes are parsed strictly from the schema to ensure type consistency and structural integrity without hard-coded model definitions.

### Core Directive

> **NO Hard-Coded Models:** The system generates Pydantic models dynamically at runtime based on the blueprint. Direct model imports (e.g., `from models import PostboxRecord`) are strictly prohibited. All validation logic is driven by the schema metadata.

### Blueprint Architectures

DaemonValidate supports two primary blueprint architectures:

#### 1. **Schema-Driven YAML/JSON Blueprints**

```yaml
# Example schema blueprint for Postbox records
fields:
  company_id: "integer"
  postbox_id: "integer"
  day_of_week: "integer"
  valid_postmark_count: "integer"
  non_mail_count: "integer"
  other_issues_count: "integer"
  total_transactions: "integer"
  transaction_date: "date"
  misplaced_item_flag: "boolean"
```

#### 2. **Live Database Schema Introspection**

DaemonValidate automatically introspects the live database schema and compiles the validation models dynamically.

## Data Ingestion Engine

### Operational Overview

DaemonValidate implements a **multi-stage streaming pipeline** that ingests data from heterogeneous sources, validates it against runtime-compiled schemas, and routes it to dedicated storage sinks. The system operates in a zero-buffering mode, processing records individually to maintain a flat memory profile regardless of dataset size.

### Ingestion Workflow

1. **Source Connection:** Establish a connection to the data source (PostgreSQL, DuckDB, or file system).
2. **Schema Acquisition:** Acquire the operational schema for validation. This is achieved by:
   - Reading the schema from an external blueprint (e.g., `schema.yaml`).
   - Querying the live database schema via `psycopg` connection introspection.
   - Loading a default schema if none is provided.
3. **Dynamic Model Compilation:** The system compiles Pydantic models at runtime based on the acquired schema. This enables zero-configuration data ingestion, as no hard-coded models are required.
4. **Data Streaming:** The source data is streamed row-by-row using `csv.DictReader`. This ensures that the memory footprint remains constant ($O(1)$) regardless of the dataset size.
5. **Validation & Routing:** Each row is validated against the dynamically compiled model. Valid records are routed to the `valid` sink, while anomalous records are routed to the `quarantine` sink.
6. **Telemetry Logging:** Execution metrics, including validation results and runtime statistics, are automatically logged to the operational database.

## 🚀 Quickstart

### Installation

```bash
# Create virtual environment (recommended)
uv init
uv sync
```

### Execution Flow
Initialise the dynamic configurations, compile your blueprint, and process an operational stream:

```python
from pathlib import Path
from daemonvalidate.config import DaemonConfig
from daemonvalidate.loaders import YamlSchemaLoader
from daemonvalidate.models import compile_dynamic_model
from daemonvalidate.core import PostboxProcessor
from daemonvalidate.telemetry import TelemetryLogger

# 1. Load configuration and paths
config = DaemonConfig(Path("daemon_config.yaml"))
workspace_dir = config.base_run_dir / "20260717" / "run-unique-id"

# 2. Compile model from blueprint
loader = YamlSchemaLoader("sales_blueprint.yaml")
SalesModel = compile_dynamic_model("SalesModel", loader.load_schema())

# 3. Stream and process rows
processor = PostboxProcessor(SalesModel)
result = processor.process_csv_stream(
    input_path=Path("raw_feed.csv"),
    output_dir=workspace_dir,
    max_error_rate=0.05, # Halt execution if failures exceed 5%
    valid_filename=config.valid_filename,
    quarantine_filename=config.quarantine_filename,
    diagnostics_filename=config.diagnostics_filename
)

# 4. Flush telemetry to database
telemetry = TelemetryLogger(config.database_path)
telemetry.log_execution("run-unique-id", "sales_edge_ingest", result["metrics"])
```

### Telemetry Database Standard
Operational run summaries are written to the validation_metrics table inside DuckDB. In accordance with internal team coding standards, the schema enforces absolute lower snake case for objects, plurals for tables, and singular variants for column fields:

```sql
SELECT 
    vm.run_id AS id,
    vm.pipeline_name AS name,
    vm.total_record AS total,
    vm.valid_record AS clean,
    vm.quarantined_record AS bad,
    vm.execution_timestamp AS executed_at
FROM validation_metrics AS vm
ORDER BY vm.execution_timestamp DESC;
```