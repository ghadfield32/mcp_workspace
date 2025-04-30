"""
MCP Setup Package

This package provides tools for setting up MCP servers in VS Code.
"""

__version__ = "0.1.0"
__author__ = "MCP Setup Team"

from mcp_setup.configurator import Configurator
from mcp_setup.validator import Validator, MCP_SERVERS
from mcp_setup.generator import Generator

__all__ = ["Configurator", "Validator", "Generator", "MCP_SERVERS"]
