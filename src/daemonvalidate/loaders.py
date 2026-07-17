import json
import yaml
from abc import ABC, abstractmethod
from typing import Dict, Any

# We import psycopg dynamically or add it to dependencies later
# to keep the core file installation decoupled if users only want local YAML/JSON.
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None  # type: ignore


class BaseSchemaLoader(ABC):
    """Abstract base class establishing the contract for fetching data schemas."""
    
    @abstractmethod
    def load_schema(self) -> Dict[str, Any]:
        """
        Fetch schema configuration and return it as a native dictionary.
        
        Returns:
            Dict[str, Any]: The raw configuration shape mapping fields to types.
        """
        pass


class YamlSchemaLoader(BaseSchemaLoader):
    """Concrete loader for parsing local YAML validation blueprints."""
    
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def load_schema(self) -> Dict[str, Any]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if not isinstance(config, dict):
                raise ValueError(f"Invalid YAML schema at {self.file_path}. Expected a key-value dictionary mapping.")
            return config


class JsonSchemaLoader(BaseSchemaLoader):
    """Concrete loader for parsing local JSON validation contracts."""
    
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def load_schema(self) -> Dict[str, Any]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            if not isinstance(config, dict):
                raise ValueError(f"Invalid JSON schema at {self.file_path}. Expected a key-value dictionary mapping.")
            return config


class PostgresSchemaLoader(BaseSchemaLoader):
    """
    Concrete loader for fetching validation schemas from a PostgreSQL configuration database.
    
    Expects a schema configuration table structure mirroring:
    SELECT configuration_layout FROM validation_schemas WHERE pipeline_name = %s
    """
    
    def __init__(self, connection_string: str, pipeline_name: str) -> None:
        if psycopg is None:
            raise ImportError(
                "The 'psycopg' library is required to use the PostgresSchemaLoader. "
                "Install it using 'pip install psycopg[binary]'."
            )
        self.connection_string = connection_string
        self.pipeline_name = pipeline_name

    def load_schema(self) -> Dict[str, Any]:
        query = """
            SELECT configuration_layout 
            FROM validation_schemas 
            WHERE pipeline_name = %s;
        """
        
        # Connect using the explicit dictionary row factory for predictable mapping
        with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (self.pipeline_name,))
                row = cur.fetchone()
                
                if not row:
                    raise ValueError(
                        f"No validation schema found in database for pipeline: '{self.pipeline_name}'."
                    )
                
                config = row["configuration_layout"]
                
                # If stored as a text/varchar block instead of native JSONB, parse it safely
                if isinstance(config, str):
                    config = json.loads(config)
                    
                if not isinstance(config, dict):
                    raise ValueError(
                        f"Database schema layout for '{self.pipeline_name}' must resolve to a dictionary shape."
                    )
                    
                return config