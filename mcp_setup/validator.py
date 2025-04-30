# mcp_setup/validator.py
"""
MCP Setup Validator Module

This module validates environment variables and files required for MCP setup.
"""
import os
import pathlib
from typing import Dict, List, Optional, Any
from mcp_setup.configurator import Configurator

# ──────────────────────────────────────────────────────────────────────────────
# Compute the repository root once, then build our relative path to the
# code-executor bundle:
ROOT = pathlib.Path(__file__).resolve().parent.parent
CODE_EXECUTOR_JS = ROOT / "mcp_code_executor" / "build" / "index.js"
# ──────────────────────────────────────────────────────────────────────────────

# Define MCP servers with their required environment variables and files
MCP_SERVERS = {
    "Code Executor": {
        "type": "stdio",
        "command": [
            "node",
            str(CODE_EXECUTOR_JS)       # ← absolute path, but computed at runtime
        ],
        "env_vars": ["CONDA_ENV_NAME", "CODE_STORAGE_DIR"],
        "files": []
    },
    "Snowflake": {
        "type": "stdio",
        "command": ["npx", "mcp_snowflake_server"],
        "env_vars": [
            "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE",
            "SNOWFLAKE_SCHEMA"
        ],
        "files": []
    },
    "Jupyter": {
        "type": "stdio",
        "template": "jupyter-docker",
        "env_vars": ["JUPYTER_URL", "JUPYTER_TOKEN", "NOTEBOOK_PATH"],
        "files": []
    },
    "OracleDB": {
        "type": "stdio",
        "command": ["docker", "run", "-i", "--rm", "dmeppiel/oracle-mcp-server"],
        "env_vars": ["ORACLE_CONNECTION_STRING", "TARGET_SCHEMA"],
        "files": []
    },
    "nba_mcp Docs": {
        "type": "sse",
        "url": "https://gitmcp.io/ghadfield32/nba_mcp",
        "env_vars": [],
        "files": []
    },
    "Gitingest-MCP": {
        # Launch through uvx so we don’t rely on npx / global npm
        "type": "stdio",
        "command": [
            # the uvx absolute path is looked-up at runtime; see build_mcp_config
            "uvx",
            "--from", "git+https://github.com/puravparab/gitingest-mcp",
            "gitingest-mcp"
        ],
        "env_vars": [],
        "files": []
    }
}


class Validator:
    """
    Validates environment variables and files required for MCP setup.
    """
    def __init__(self, configurator: Optional[Configurator] = None):
        """
        Initialize the validator with a configurator.

        Args:
            configurator: Configurator instance
        """
        self.configurator = configurator or Configurator()

    def list_servers(self) -> List[str]:
        """List all available MCP servers."""
        return list(MCP_SERVERS.keys())

    def get_server_config(self, name: str) -> Dict[str, Any]:
        """Get the configuration for a specific server."""
        return MCP_SERVERS.get(name, {})

    def validate_server(self, name: str) -> Dict[str, Any]:
        """
        Validate environment variables and files for a server.
        Returns a dict: { valid: bool, missing_env: [...], missing_files: [...] }
        """
        if name not in MCP_SERVERS:
            return {
                "valid": False,
                "error": f"Unknown server: {name}",
                "missing_env": [],
                "missing_files": []
            }

        server_config = MCP_SERVERS[name]
        missing_env = [
            var for var in server_config.get("env_vars", [])
            if not os.environ.get(var)
        ]
        missing_files = [
            fp for fp in server_config.get("files", [])
            if not pathlib.Path(fp).is_file()
        ]

        return {
            "valid": not missing_env and not missing_files,
            "missing_env": missing_env,
            "missing_files": missing_files
        }

    def validate_servers(self, server_names: List[str]) -> Dict[str, Dict[str, Any]]: 
        """Validate multiple servers at once."""
        return {name: self.validate_server(name) for name in server_names}


if __name__ == "__main__":
    validator = Validator()
    print("Available servers:", validator.list_servers())
    print("Jupyter validation:", validator.validate_server("Jupyter"))

