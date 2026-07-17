import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

class DaemonConfig:
    """Manages system-wide operational overrides and paths for the Daemon Suite."""
    
    def __init__(self, config_path: Optional[Path] = None) -> None:
        # Resolve path absolutely based on execution context
        self.config_path = (config_path or Path("daemon_config.yaml")).resolve()
        self.settings: Dict[str, Any] = self._load_defaults()
        
        if self.config_path.exists():
            self._load_from_file()
        else:
            print(f"--- WARNING: Configuration file not found at {self.config_path}. Using system defaults. ---")

    def _load_defaults(self) -> Dict[str, Any]:
        """Provides fallback configurations matching a standard local environment."""
        base_dir = Path.cwd().resolve()
        return {
            "database": {
                "path": str(base_dir / "daemonflow.duckdb")
            },
            "storage": {
                "base_run_dir": str(base_dir / ".daemon_runs"),
                "valid_filename": "valid.csv",
                "quarantine_filename": "quarantine.csv",
                "diagnostics_filename": "diagnostics.jsonl"
            }
        }

    def _load_from_file(self) -> None:
        """Overlays user configuration choices cleanly over structural defaults."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            user_data = yaml.safe_load(f)
            if isinstance(user_data, dict):
                if "database" in user_data and isinstance(user_data["database"], dict):
                    # Direct check: if path is provided, resolve it relative to config location
                    if "path" in user_data["database"]:
                        raw_path = Path(user_data["database"]["path"])
                        if not raw_path.is_absolute():
                            # If they gave a relative path, calculate it relative to the config file's location
                            raw_path = (self.config_path.parent / raw_path).resolve()
                        self.settings["database"]["path"] = str(raw_path)
                        
                if "storage" in user_data and isinstance(user_data["storage"], dict):
                    self.settings["storage"].update(user_data["storage"])

    @property
    def database_path(self) -> Path:
        return Path(self.settings["database"]["path"])

    @property
    def base_run_dir(self) -> Path:
        return Path(self.settings["storage"]["base_run_dir"])

    @property
    def valid_filename(self) -> str:
        return self.settings["storage"]["valid_filename"]

    @property
    def quarantine_filename(self) -> str:
        return self.settings["storage"]["quarantine_filename"]

    @property
    def diagnostics_filename(self) -> str:
        # Corrected from "storagesettings" to "storage"
        return self.settings["storage"]["diagnostics_filename"]