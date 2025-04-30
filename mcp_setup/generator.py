"""
MCP Setup Generator Module

This module handles the generation and writing of the `.vscode/mcp.json` configuration file.
"""

import os
import json
import pathlib
import socket
import sys                        # ← to detect platform
from typing import Dict, List, Any, Optional

from mcp_setup.validator import Validator, MCP_SERVERS

class Generator:
    def __init__(self,
                 validator: Optional[Validator] = None,
                 env_file: str = ".env"):
        self.validator = validator or Validator()
        self.env_file  = env_file
        self.output_dir  = ".vscode"
        self.output_file = "mcp.json"


    def build_mcp_config(self, server_names: List[str]) -> Dict[str, Any]:
        """
        Build .vscode/mcp.json, with OS-aware Jupyter networking:
        - Linux/macOS: port-map if free, else --network host
        - Windows: port-map if free, else drop port mapping
        """
        import shutil, socket, sys

        def is_port_free(port: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                    return True
                except OSError:
                    return False

        cfg: Dict[str, Any] = {"servers": {}}
        on_windows = sys.platform.startswith("win")

        for name in server_names:
            scfg = MCP_SERVERS.get(name)
            if not scfg:
                print(f"[WARN] Unknown server '{name}' – skipped.")
                continue

            # --- Jupyter special case ---
            if scfg.get("template") == "jupyter-docker":
                missing = [v for v in scfg["env_vars"] if not os.getenv(v)]
                if missing:
                    print(f"[ERROR] Missing {missing} for Jupyter – skipping.")
                    continue

                url      = os.environ["JUPYTER_URL"]
                token    = os.environ["JUPYTER_TOKEN"]
                notebook = os.environ["NOTEBOOK_PATH"]

                docker_args = ["run", "-i", "--rm"]

                # Linux/macOS host-network override
                if not on_windows and os.getenv("MCP_HOST_NET","").lower() == "true":
                    docker_args += ["--network", "host"]
                else:
                    # Decide whether to port-map
                    if is_port_free(8888):
                        docker_args += [
                            "-e", "DOCKER_DEFAULT_PLATFORM=linux/amd64",
                            "-p", "8888:8888"
                        ]
                    else:
                        if on_windows:
                            print(
                              "[WARN] Port 8888 busy on host; skipping `-p 8888:8888`. "
                              "Container will reach your Jupyter at host.docker.internal:8888."
                            )
                            # no port-map
                        else:
                            # Linux/mac fallback
                            print(
                              "[INFO] Port 8888 busy; using --network host for Jupyter."
                            )
                            docker_args += ["--network", "host"]

                # Always point container at host.docker.internal
                docker_args += [
                    "-e", f"SERVER_URL={url}",
                    "-e", f"TOKEN={token}",
                    "-e", f"NOTEBOOK_PATH={notebook}",
                    "datalayer/jupyter-mcp-server:latest"
                ]

                cfg["servers"][name] = {
                    "type":    "stdio",
                    "command": "docker",
                    "args":    docker_args
                }
                continue

            # --- Default stdio servers ---
            if scfg["type"] == "stdio":
                cmd = list(scfg["command"])
                if cmd[0] == "uvx" and shutil.which("uvx"):
                    cmd[0] = shutil.which("uvx")
                if cmd[0] == "npx" and not shutil.which("npx"):
                    if shutil.which("uvx"):
                        print(f"[INFO] Replacing missing npx with uvx for {name}")
                        cmd[0] = shutil.which("uvx")
                    else:
                        print(f"[ERROR] Neither 'npx' nor 'uvx' found – {name} will fail.")

                entry = {"type": "stdio", "command": cmd[0]}
                if len(cmd) > 1:
                    entry["args"] = cmd[1:]
                entry["envFile"] = f"${{workspaceFolder}}/{self.env_file}"
                if scfg.get("env_vars"):
                    entry["env"] = {v: os.getenv(v, "") for v in scfg["env_vars"]}

                cfg["servers"][name] = entry
                continue

            # --- SSE servers ---
            if scfg["type"] == "sse":
                url = scfg.get("url") or os.getenv(scfg.get("url_env",""), "")
                if not url:
                    print(f"[WARN] No URL for '{name}' – skipped.")
                    continue
                entry = {"type": "sse", "url": url}
                if scfg.get("env_vars"):
                    entry["env"] = {v: os.getenv(v, "") for v in scfg["env_vars"]}
                cfg["servers"][name] = entry

        return cfg



    def write_mcp_config(self, config: Dict[str, Any]) -> str:
        """
        Write the MCP configuration to file.

        Args:
            config: MCP configuration dictionary

        Returns:
            Path to the written configuration file
        """
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, self.output_file)

        # Use utf-8 explicitly
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        return output_path

    def generate_mcp_config(self, server_names: List[str]) -> Dict[str, Any]:
        """
        Generate MCP configuration for selected servers and write to file.

        Args:
            server_names: List of server names

        Returns:
            Dictionary with generation result, including:
                - config: Generated configuration
                - output_path: Path to the written configuration file
                - success: Whether the generation was successful
        """
        try:
            # Build configuration
            config = self.build_mcp_config(server_names)

            # Write configuration to file
            output_path = self.write_mcp_config(config)

            return {
                "success": True,
                "config": config,
                "output_path": output_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


if __name__ == "__main__":
    # Example usage
    generator = Generator()

    # Generate MCP configuration for selected servers
    server_names = ["Jupyter", "Code Executor"]
    result = generator.generate_mcp_config(server_names)

    if result["success"]:
        print(f"Configuration written to {result['output_path']}")
        print("Configuration:")
        print(json.dumps(result["config"], indent=2))
    else:
        print(f"Error generating configuration: {result['error']}")
