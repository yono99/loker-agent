"""Environment variable loader with .env file support."""

import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv


class EnvLoader:
    """Load and validate environment variables from .env file."""

    _instance = None
    _loaded = False

    def __new__(cls):
        """Singleton pattern to ensure .env is loaded only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize and load .env file if not already loaded."""
        if not self._loaded:
            self._load_env()
            self._loaded = True

    def _load_env(self, env_file: Optional[str] = None) -> None:
        """Load environment variables from .env file.
        
        Args:
            env_file: Path to .env file. If None, searches from current directory up to root.
        """
        if env_file:
            load_dotenv(env_file, override=True)
            return
        
        # Search for .env file in current directory and parent directories
        current_dir = Path.cwd()
        for parent in [current_dir] + list(current_dir.parents):
            env_path = parent / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=True)
                return
        
        # Fallback: try .env in project root (assuming this file is in core/)
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)

    def get_required(self, key: str) -> str:
        """Get a required environment variable.
        
        Args:
            key: Environment variable key.
        
        Returns:
            Value of the environment variable.
        
        Raises:
            ValueError: If the variable is not set.
        """
        value = os.environ.get(key)
        if value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value

    def get_optional(self, key: str, default: Any = None) -> Optional[str]:
        """Get an optional environment variable with default value.
        
        Args:
            key: Environment variable key.
            default: Default value if variable is not set.
        
        Returns:
            Value of the environment variable or default.
        """
        return os.environ.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean environment variable.
        
        Args:
            key: Environment variable key.
            default: Default value if variable is not set.
        
        Returns:
            Boolean value (true/1/yes/on) or default.
        """
        value = os.environ.get(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """Get an integer environment variable.
        
        Args:
            key: Environment variable key.
            default: Default value if variable is not set.
        
        Returns:
            Integer value or default.
        
        Raises:
            ValueError: If value is not a valid integer.
        """
        value = os.environ.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Environment variable '{key}' must be an integer, got '{value}'")

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """Get a float environment variable.
        
        Args:
            key: Environment variable key.
            default: Default value if variable is not set.
        
        Returns:
            Float value or default.
        
        Raises:
            ValueError: If value is not a valid float.
        """
        value = os.environ.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Environment variable '{key}' must be a float, got '{value}'")

    def get_list(self, key: str, separator: str = ",", default: Optional[List[str]] = None) -> List[str]:
        """Get a list environment variable.
        
        Args:
            key: Environment variable key.
            separator: Separator for splitting values.
            default: Default list if variable is not set.
        
        Returns:
            List of values or default.
        """
        value = os.environ.get(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]

    def get_dict(self, key: str, default: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get a dictionary environment variable (format: key1=value1,key2=value2).
        
        Args:
            key: Environment variable key.
            default: Default dict if variable is not set.
        
        Returns:
            Dictionary of key-value pairs or default.
        """
        value = os.environ.get(key)
        if value is None:
            return default or {}
        result = {}
        for item in value.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    def validate_required(self, keys: List[str]) -> bool:
        """Validate that all required keys are present.
        
        Args:
            keys: List of required environment variable keys.
        
        Returns:
            True if all keys are present.
        
        Raises:
            ValueError: If any required key is missing.
        """
        missing = [key for key in keys if os.environ.get(key) is None]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        return True

    def reload(self, env_file: Optional[str] = None) -> None:
        """Reload environment variables from .env file.
        
        Args:
            env_file: Path to .env file. If None, uses default search.
        """
        self._load_env(env_file)

    def get_all(self) -> Dict[str, str]:
        """Get all environment variables as a dictionary.
        
        Returns:
            Dictionary of all environment variables.
        """
        return dict(os.environ)
