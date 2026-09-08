"""Configuration manager with environment variable support and encryption."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from copy import deepcopy
from jsonschema import validate, ValidationError

from core.env_loader import EnvLoader
from core.encryption import EncryptionManager


class ConfigManager:
    """Manage configuration with environment variables, JSON support, and encryption."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for ConfigManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        env_prefix: str = "LOKER",
        encryption_key: Optional[str] = None,
    ):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to JSON config file.
            env_prefix: Prefix for environment variables.
            encryption_key: Key for encrypted config values.
        """
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self._config_file = Path(config_file) if config_file else None
        self._env_prefix = env_prefix
        self._config: Dict[str, Any] = {}
        self._env_loader = EnvLoader()
        self._encryption = EncryptionManager(encryption_key) if encryption_key else None
        self._schema: Optional[Dict[str, Any]] = None
        self._environment = self._detect_environment()
        self._initialized = True
        
        # Auto-load if config file exists
        if self._config_file and self._config_file.exists():
            self.load(self._config_file)

    def _detect_environment(self) -> str:
        """Detect current environment.
        
        Returns:
            'development', 'production', 'testing', or 'default'.
        """
        env = os.environ.get(f"{self._env_prefix}_ENV", "").lower()
        if env in ["development", "dev", "local"]:
            return "development"
        elif env in ["production", "prod"]:
            return "production"
        elif env in ["testing", "test"]:
            return "testing"
        return "default"

    def set_schema(self, schema: Dict[str, Any]) -> None:
        """Set JSON schema for config validation.
        
        Args:
            schema: JSON schema dict.
        """
        self._schema = schema

    def load(self, config_file: Union[str, Path]) -> None:
        """Load configuration from JSON file.
        
        Args:
            config_file: Path to JSON config file.
        
        Raises:
            FileNotFoundError: If config file doesn't exist.
            json.JSONDecodeError: If JSON is invalid.
        """
        config_file = Path(config_file)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file, "r") as f:
            raw_config = json.load(f)
        
        # Process encrypted values
        self._config = self._process_encrypted_values(raw_config)
        
        # Resolve environment variables
        self._config = self._resolve_env_vars(self._config)
        
        # Load environment-specific config
        env_config = self._get_environment_config(raw_config)
        if env_config:
            self._config = self._deep_merge(self._config, env_config)
        
        self._config_file = config_file

    def _process_encrypted_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process encrypted values in config.
        
        Values with format "{encrypted: <base64>}" are decrypted.
        """
        result = {}
        for key, value in config.items():
            if isinstance(value, dict):
                result[key] = self._process_encrypted_values(value)
            elif isinstance(value, str) and value.startswith("{encrypted: ") and value.endswith("}"):
                if self._encryption:
                    encrypted_data = value[11:-1].strip()
                    try:
                        result[key] = self._encryption.decrypt(encrypted_data)
                    except Exception as e:
                        result[key] = value  # Keep as is if decryption fails
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    def _get_environment_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract environment-specific configuration.
        
        Looks for key like "development", "production", "testing" in config.
        """
        for key in [self._environment, f"{self._environment}_config"]:
            if key in config and isinstance(config[key], dict):
                return config[key]
        
        # Try to find by env name without prefix
        for key in config:
            if key.lower() == self._environment:
                if isinstance(config[key], dict):
                    return config[key]
        
        return {}

    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variable placeholders in config.
        
        Placeholder format: ${ENV_VAR} or ${ENV_VAR:default}
        """
        result = {}
        for key, value in config.items():
            if isinstance(value, dict):
                result[key] = self._resolve_env_vars(value)
            elif isinstance(value, str):
                result[key] = self._resolve_env_var(value)
            else:
                result[key] = value
        return result

    def _resolve_env_var(self, value: str) -> str:
        """Resolve a single environment variable placeholder."""
        import re
        
        pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'
        
        def replace_match(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default)
        
        return re.sub(pattern, replace_match, value)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    def save(self, config_file: Optional[Union[str, Path]] = None) -> None:
        """Save current configuration to JSON file.
        
        Args:
            config_file: Path to save config. If None, uses the loaded file path.
        
        Raises:
            ValueError: If no config file path is available.
        """
        config_file = Path(config_file) if config_file else self._config_file
        if not config_file:
            raise ValueError("No config file path specified")
        
        # Create parent directory if needed
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, "w") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g., "database.host").
            default: Default value if key not found.
        
        Returns:
            Configuration value or default.
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g., "database.host").
            value: Value to set.
        """
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_env(self, key: str, default: Any = None) -> str:
        """Get environment variable with prefix.
        
        Args:
            key: Environment variable key (without prefix).
            default: Default value if not set.
        
        Returns:
            Value of environment variable.
        """
        env_key = f"{self._env_prefix}_{key}".upper()
        return self._env_loader.get_optional(env_key, default)

    def get_env_required(self, key: str) -> str:
        """Get required environment variable with prefix.
        
        Args:
            key: Environment variable key (without prefix).
        
        Returns:
            Value of environment variable.
        
        Raises:
            ValueError: If variable is not set.
        """
        env_key = f"{self._env_prefix}_{key}".upper()
        return self._env_loader.get_required(env_key)

    def validate(self) -> bool:
        """Validate configuration against schema.
        
        Returns:
            True if valid.
        
        Raises:
            ValidationError: If validation fails.
        """
        if self._schema is None:
            return True
        
        try:
            validate(instance=self._config, schema=self._schema)
            return True
        except ValidationError as e:
            raise ValidationError(f"Config validation failed: {e.message}")

    def encrypt_value(self, value: str) -> str:
        """Encrypt a value for config storage.
        
        Args:
            value: Value to encrypt.
        
        Returns:
            Encrypted string in format "{encrypted: <base64>}"
        
        Raises:
            RuntimeError: If encryption is not configured.
        """
        if not self._encryption:
            raise RuntimeError("Encryption not configured. Provide encryption_key.")
        
        encrypted = self._encryption.encrypt(value)
        return f"{{encrypted: {encrypted}}}"

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration.
        
        Returns:
            Deep copy of configuration.
        """
        return deepcopy(self._config)

    def reload(self) -> None:
        """Reload configuration from file."""
        if self._config_file and self._config_file.exists():
            self.load(self._config_file)

    @property
    def environment(self) -> str:
        """Get current environment."""
        return self._environment

    def get_environment_config(self, env_name: str) -> Dict[str, Any]:
        """Get configuration for a specific environment.
        
        Args:
            env_name: Environment name (e.g., 'development', 'production').
        
        Returns:
            Environment-specific configuration.
        """
        if self._config_file and self._config_file.exists():
            with open(self._config_file, "r") as f:
                raw_config = json.load(f)
            
            env_config = {}
            for key in [env_name, f"{env_name}_config"]:
                if key in raw_config and isinstance(raw_config[key], dict):
                    env_config = self._deep_merge(env_config, raw_config[key])
            
            return env_config
        return {}

    def merge_environment_config(self, env_name: Optional[str] = None) -> None:
        """Merge configuration for a specific environment.
        
        Args:
            env_name: Environment name. If None, uses current environment.
        """
        env = env_name or self._environment
        env_config = self.get_environment_config(env)
        if env_config:
            self._config = self._deep_merge(self._config, env_config)

    def to_env(self, prefix: Optional[str] = None) -> Dict[str, str]:
        """Convert configuration to environment variables format.
        
        Args:
            prefix: Prefix for environment variables. If None, uses instance prefix.
        
        Returns:
            Dictionary of environment variable key-value pairs.
        """
        prefix = (prefix or self._env_prefix).upper()
        result = {}
        self._flatten_dict(self._config, prefix, result)
        return result

    def _flatten_dict(self, config: Dict[str, Any], prefix: str, result: Dict[str, str]) -> None:
        """Flatten a nested dictionary into environment variables."""
        for key, value in config.items():
            full_key = f"{prefix}_{key}".upper()
            if isinstance(value, dict):
                self._flatten_dict(value, full_key, result)
            else:
                if isinstance(value, (list, dict)):
                    result[full_key] = json.dumps(value)
                else:
                    result[full_key] = str(value)
