"""
MCP Setup Configurator Module

This module handles server configurations and environment loading logic for MCP setup.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class Configurator:
    """
    Handles configuration loading and management for MCP setup.
    """
    def __init__(self, env_file: str = ".env"):
        """
        Initialize the configurator with an environment file.

        Args:
            env_file: Path to the environment file (.env)
        """
        self.env_file = env_file
        self.env_vars = {}
        self.config = {}

    def load_environment(self) -> Dict[str, str]:
        """
        Load environment variables from the .env file into both:
        - a returned dict, and
        - os.environ (so Validator sees them).
        Inline comments (after '#') are stripped automatically.
        """
        env_vars: Dict[str,str] = {}
        if not os.path.exists(self.env_file):
            print(f"⚠️ Warning: Environment file {self.env_file} not found.")
            return env_vars

        # Open as UTF-8, ignore bad bytes, and strip inline comments
        with open(self.env_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, raw_value = line.split("=", 1)
                    key = key.strip()

                    # Drop anything after a '#' (inline comment)
                    val = raw_value.split("#", 1)[0].strip().strip("'\"")

                    env_vars[key] = val
                    os.environ[key] = val
                    print(f"🔍 Loaded {key}={val}")  # debug log

        self.env_vars = env_vars
        return env_vars



    def get_server_config(self, server_type: str) -> Dict[str, Any]:
        """
        Get server configuration based on server type.

        Args:
            server_type: Type of server (e.g., "production", "development")

        Returns:
            Server configuration dictionary
        """
        # Default configurations based on server type
        configs = {
            "production": {
                "debug": False,
                "host": self.env_vars.get("PROD_HOST", "localhost"),
                "port": int(self.env_vars.get("PROD_PORT", "8080")),
                "workers": 4
            },
            "development": {
                "debug": True,
                "host": self.env_vars.get("DEV_HOST", "localhost"),
                "port": int(self.env_vars.get("DEV_PORT", "8000")),
                "workers": 1
            },
            "testing": {
                "debug": True,
                "host": "localhost",
                "port": 8888,
                "workers": 1
            }
        }

        return configs.get(server_type, configs["development"])

    def load_json_config(self, config_file: str) -> Dict[str, Any]:
        """
        Load configuration from a JSON file.

        Args:
            config_file: Path to the JSON configuration file

        Returns:
            Configuration dictionary
        """
        if not os.path.exists(config_file):
            print(f"Warning: Configuration file {config_file} not found.")
            return {}

        with open(config_file, "r") as f:
            config = json.load(f)

        self.config = config
        return config

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)


if __name__ == "__main__":
    # Example usage
    configurator = Configurator()
    env_vars = configurator.load_environment()
    print("Environment Variables:", env_vars)

    server_config = configurator.get_server_config("development")
    print("Server Configuration:", server_config)
