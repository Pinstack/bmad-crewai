"""Secure configuration and credential management for BMAD CrewAI."""

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import keyring
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Configuration for API integrations."""

    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    model: Optional[str] = None  # AI model to use
    fallback_model: Optional[str] = None  # Fallback AI model


@dataclass
class BMADConfig:
    """BMAD-specific configuration."""

    core_path: str = ".bmad-core"
    qa_location: str = "docs/qa"
    stories_location: str = "docs/stories"
    enable_logging: bool = True
    log_level: str = "INFO"


class CredentialStore:
    """Secure credential storage with multiple backends."""

    def __init__(self, app_name: str = "bmad-crewai"):
        self.app_name = app_name
        self._encryption_key = self._get_or_create_key()

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for sensitive data."""
        key_file = Path.home() / ".bmad-crewai" / "encryption.key"

        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()

        # Create new key
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)

        # Set restrictive permissions
        key_file.chmod(0o600)
        return key

    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        f = Fernet(self._encryption_key)
        return f.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        f = Fernet(self._encryption_key)
        return f.decrypt(encrypted_data.encode()).decode()

    def store_credential(
        self, service: str, username: str, password: str, use_keyring: bool = True
    ) -> None:
        """Store credential securely."""
        if use_keyring:
            try:
                keyring.set_password(self.app_name, f"{service}:{username}", password)
                logger.info(f"Stored credential for {service}:{username} in keyring")
            except Exception as e:
                logger.warning(
                    f"Keyring not available, falling back to encrypted file: {e}"
                )
                use_keyring = False

        if not use_keyring:
            # Fallback to encrypted file storage
            cred_file = Path.home() / ".bmad-crewai" / "credentials.json"
            cred_file.parent.mkdir(parents=True, exist_ok=True)

            credentials = {}
            if cred_file.exists():
                with open(cred_file, "r") as f:
                    encrypted_creds = json.load(f)
                    for k, v in encrypted_creds.items():
                        credentials[k] = self._decrypt(v)

            credentials[f"{service}:{username}"] = password

            # Re-encrypt and save
            encrypted_creds = {k: self._encrypt(v) for k, v in credentials.items()}
            with open(cred_file, "w") as f:
                json.dump(encrypted_creds, f, indent=2)

            cred_file.chmod(0o600)
            logger.info(f"Stored credential for {service}:{username} in encrypted file")

    def get_credential(
        self, service: str, username: str, use_keyring: bool = True
    ) -> Optional[str]:
        """Retrieve credential securely."""
        if use_keyring:
            try:
                return keyring.get_password(self.app_name, f"{service}:{username}")
            except Exception as e:
                logger.warning(f"Keyring not available: {e}")
                use_keyring = False

        if not use_keyring:
            # Fallback to encrypted file
            cred_file = Path.home() / ".bmad-crewai" / "credentials.json"
            if cred_file.exists():
                try:
                    with open(cred_file, "r") as f:
                        encrypted_creds = json.load(f)
                        encrypted_password = encrypted_creds.get(
                            f"{service}:{username}"
                        )
                        if encrypted_password:
                            return self._decrypt(encrypted_password)
                except Exception as e:
                    logger.error(f"Failed to read credentials file: {e}")

        return None


class ConfigManager:
    """Central configuration management."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(
            config_file or (Path.home() / ".bmad-crewai" / "config.json")
        )
        self.credential_store = CredentialStore()
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment."""
        config = {
            "bmad": asdict(BMADConfig()),
            "apis": {},
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        }

        # Load from config file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    file_config = json.load(f)
                    self._deep_update(config, file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

        # Override with environment variables
        self._load_from_env(config)

        return config

    def _load_from_env(self, config: Dict[str, Any]) -> None:
        """Load configuration from environment variables."""
        # BMAD configuration
        if "BMAD_CORE_PATH" in os.environ:
            config["bmad"]["core_path"] = os.environ["BMAD_CORE_PATH"]
        if "BMAD_QA_LOCATION" in os.environ:
            config["bmad"]["qa_location"] = os.environ["BMAD_QA_LOCATION"]
        if "BMAD_STORIES_LOCATION" in os.environ:
            config["bmad"]["stories_location"] = os.environ["BMAD_STORIES_LOCATION"]

        # API configurations
        for key, value in os.environ.items():
            if key.startswith("API_") and "_KEY" in key:
                provider = key.replace("API_", "").replace("_KEY", "").lower()
                config["apis"][provider] = {"provider": provider, "api_key": value}

        # OpenRouter specific configuration
        if "OPENROUTER_API_KEY" in os.environ:
            config["apis"]["openrouter"] = {
                "provider": "openrouter",
                "api_key": os.environ["OPENROUTER_API_KEY"],
                "base_url": "https://openrouter.ai/api/v1",
                "model": os.environ.get(
                    "OPENROUTER_MODEL", "openrouter/sonoma-sky-alpha"
                ),
                "fallback_model": os.environ.get(
                    "OPENROUTER_FALLBACK_MODEL", "openrouter/sonoma-dusk-alpha"
                ),
            }

        # Logging
        if "LOG_LEVEL" in os.environ:
            config["logging"]["level"] = os.environ["LOG_LEVEL"]

    def _deep_update(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep update nested dictionaries."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def get_api_config(self, provider: str) -> APIConfig:
        """Get API configuration for a provider."""
        api_config = self._config["apis"].get(provider, {})
        return APIConfig(**api_config)

    def set_api_config(self, provider: str, config: APIConfig) -> None:
        """Set API configuration for a provider."""
        self._config["apis"][provider] = asdict(config)
        self.save()

    def get_bmad_config(self) -> BMADConfig:
        """Get BMAD configuration."""
        return BMADConfig(**self._config["bmad"])

    def set_bmad_config(self, config: BMADConfig) -> None:
        """Set BMAD configuration."""
        self._config["bmad"] = asdict(config)
        self.save()

    def save(self) -> None:
        """Save configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            # Don't save API keys to file for security
            safe_config = self._config.copy()
            for api_config in safe_config["apis"].values():
                if "api_key" in api_config:
                    api_config["api_key"] = None

            json.dump(safe_config, f, indent=2)

    def store_api_key(self, provider: str, api_key: str) -> None:
        """Store API key securely."""
        self.credential_store.store_credential("api", provider, api_key)

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key from secure storage."""
        # First try environment variable
        env_key = f"API_{provider.upper()}_KEY"
        if env_key in os.environ:
            return os.environ[env_key]

        # Then try secure storage
        return self.credential_store.get_credential("api", provider)
