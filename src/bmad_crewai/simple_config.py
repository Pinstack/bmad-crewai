"""Simple configuration for BMAD CrewAI MVP."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class SimpleConfig:
    """Simple configuration management for MVP."""

    def __init__(self):
        self.config_dir = Path.home() / ".bmad-crewai"
        self.config_file = self.config_dir / "config.json"
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment and file."""
        config = {"apis": {}, "bmad_core_path": ".bmad-core"}

        # Load from config file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config.update(json.load(f))
            except Exception:
                pass  # Ignore config file errors for MVP

        # Override with environment variables
        for key, value in os.environ.items():
            if key.startswith("API_") and "_KEY" in key:
                provider = key.replace("API_", "").replace("_KEY", "").lower()
                config["apis"][provider] = {"api_key": value}

        return config

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key from environment or config."""
        # First check environment
        env_key = f"API_{provider.upper()}_KEY"
        if env_key in os.environ:
            return os.environ[env_key]

        # Then check config file
        api_config = self._config["apis"].get(provider, {})
        return api_config.get("api_key")

    def save_api_key(self, provider: str, api_key: str) -> None:
        """Save API key to config file."""
        if "apis" not in self._config:
            self._config["apis"] = {}

        self._config["apis"][provider] = {"api_key": api_key}
        self._save()

    def _save(self) -> None:
        """Save configuration."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self._config, f, indent=2)
