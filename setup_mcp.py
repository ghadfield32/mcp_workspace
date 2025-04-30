#!/usr/bin/env python3
"""
MCP Setup CLI

This module provides a command-line interface for setting up MCP servers in VS Code.
"""
import os
import sys
import argparse
import json
from typing import List, Dict, Any, Optional

from mcp_setup.configurator import Configurator
from mcp_setup.validator import Validator
from mcp_setup.generator import Generator
from mcp_setup.validator import MCP_SERVERS

import subprocess, time, requests, importlib.util
from urllib.parse import urlparse, urljoin


def select_servers(validator: Validator) -> List[str]:
    """
    Present an interactive checklist of available MCP servers.

    Args:
        validator: Validator instance

    Returns:
        List of selected server names
    """
    servers = validator.list_servers()

    print("\nAvailable MCP Servers:")
    for i, name in enumerate(servers, 1):
        print(f"  {i}. {name}")

    print("\nSelect servers to enable (comma-separated indices, e.g., '1,3,5'):")
    choice = input("Choice: ").strip()

    selected = []
    for idx in choice.split(","):
        try:
            idx = int(idx.strip()) - 1
            if 0 <= idx < len(servers):
                selected.append(servers[idx])
        except ValueError:
            pass

    return selected



# 1) Replacement for select_servers():
def select_and_expand_servers(validator: Validator) -> List[str]:
    """
    1. Present a numbered list of available MCP servers.
    2. Let the user pick (comma-separated).
    3. For each selected server, ask if they need multiple connections.
       - If yes: prompt for labels, e.g. "prod,analytics"
       - Expand "Snowflake" → ["Snowflake:prod","Snowflake:analytics"]
    Returns the final list of server identifiers.
    """
    servers = validator.list_servers()
    print("\nAvailable MCP Servers:")
    for i, name in enumerate(servers, 1):
        print(f"  {i}. {name}")
    choice = input("\nSelect servers (e.g. 1,3,5): ").strip()

    raw = []
    for idx in choice.split(","):
        try:
            n = int(idx) - 1
            if 0 <= n < len(servers):
                raw.append(servers[n])
        except:
            pass

    expanded = []
    for server in raw:
        ans = input(f"❓ Multiple connections for '{server}'? (y/N): ").strip().lower()
        if ans == "y":
            labels = input(f"Enter labels for '{server}' (comma-separated): ").strip()
            for lbl in [l.strip() for l in labels.split(",") if l.strip()]:
                expanded.append(f"{server}:{lbl}")
        else:
            expanded.append(server)
    return expanded


# 2) New helper to prompt for missing env vars:
def prompt_for_env_vars(server_ids: List[str], env_file: str):
    """
    For each 'Server[:instance]', prompt for any required env vars that
    are still missing from os.environ, then append them to the env file.
    """
    from mcp_setup.validator import MCP_SERVERS

    updates = []
    for sid in server_ids:
        base = sid.split(":",1)[0]
        required = MCP_SERVERS[base]["env_vars"]
        for var in required:
            if not os.environ.get(var):
                val = input(f"🔑 Enter value for {var} (for {base}): ").strip()
                updates.append((var, val))
                os.environ[var] = val
                print(f"✅ Set {var}={val}")
    if updates:
        with open(env_file, "a") as f:
            for k, v in updates:
                f.write(f"\n{k}={v}")
        print(f"💾 Appended {len(updates)} new values to {env_file}")


def main() -> int:
    """
    Main entry point for the MCP setup tool.

    Returns:
        Exit code (0 for success, non-zero for error)
    """

    parser = argparse.ArgumentParser(description="Setup MCP servers for VS Code")
    parser.add_argument(
        "--env", 
        choices=["dev", "stage", "prod"], 
        required=True,
        help="Environment to use (dev, stage, or prod)"
    )
    args = parser.parse_args()

    # Initialize components
    env_file = f".env.{args.env}"
    configurator = Configurator(env_file)
    validator = Validator(configurator)
    # pass the very same env_file we loaded so mcp.json points correctly
    generator = Generator(validator, env_file=os.path.basename(env_file))

    # Step 1: Load environment
    print(f"\n🔍 Loading environment from {env_file}...")
    try:
        env_vars = configurator.load_environment()
        if not env_vars:
            print(f"⚠️ Warning: No environment variables found in {env_file}.")
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        return 1

    # Step 2: Present server checklist
    selected_servers = select_servers(validator)
    if not selected_servers:
        print("❌ No servers selected. Exiting.")
        return 1

    print(f"\n📋 Selected servers: {', '.join(selected_servers)}")

    print("\n🔑 Prompting for any missing credentials…")
    prompt_for_env_vars(selected_servers, env_file)
    print("🛠️  Environment now contains:", 
        ", ".join(k for k in MCP_SERVERS.get(selected_servers[0].split(':')[0], {}).get("env_vars", []) 
                    if k in os.environ))

    # Step 3: Validate servers
    print("\n🔍 Validating selected servers...")
    validation_results = validator.validate_servers(selected_servers)

    valid_servers = []
    invalid_servers = []

    for name, result in validation_results.items():
        if result["valid"]:
            valid_servers.append(name)
            print(f"  ✅ {name}: Valid")
        else:
            invalid_servers.append((name, result))
            missing_env = result.get("missing_env", [])
            missing_files = result.get("missing_files", [])

            print(f"  ❌ {name}: Invalid")
            if missing_env:
                print(f"     - Missing environment variables: {', '.join(missing_env)}")
            if missing_files:
                print(f"     - Missing files: {', '.join(missing_files)}")


    # Step 4: Generate MCP configuration
    if valid_servers:
        print("\n🔧 Generating MCP configuration...")
        result = generator.generate_mcp_config(valid_servers)

        if result["success"]:
            print(f"  ✅ Configuration written to {result['output_path']}")
            config_servers = result["config"].get("servers", {})
            print(f"  ℹ️ Configured servers: {', '.join(config_servers.keys())}")
        else:
            print(f"  ❌ Error generating configuration: {result.get('error', 'Unknown error')}")
            return 1
    else:
        print("\n⚠️ No valid servers found. Configuration not generated.")
        return 1

    # Step 5: Print summary report
    print("\n📊 Setup Summary:")
    print(f"  ✅ Successfully configured: {len(valid_servers)} server(s)")
    print(f"  ❌ Failed to configure: {len(invalid_servers)} server(s)")

    if invalid_servers:
        print("\n⚠️ Failed Servers:")
        for name, result in invalid_servers:
            missing_env = result.get("missing_env", [])
            missing_files = result.get("missing_files", [])

            print(f"  • {name}:")
            if missing_env:
                print(f"    - Missing environment variables: {', '.join(missing_env)}")
            if missing_files:
                print(f"    - Missing files: {', '.join(missing_files)}")

    print("\n✨ Done. Use 'MCP: List Servers' in VS Code to verify your configuration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
