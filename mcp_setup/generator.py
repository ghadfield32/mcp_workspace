"""
MCP Setup Generator Module

This module handles the generation and writing of the `.vscode/mcp.json` configuration file.
"""
import os
import json
import pathlib
from typing import Dict, List, Optional, Any

from mcp_setup.validator import Validator, MCP_SERVERS


class Generator:
    """
    Generates and writes the `.vscode/mcp.json` configuration file.
    """
    def __init__(self, validator: Optional[Validator] = None, env_file: str = ".env"):
        """
        Initialize the generator with a validator.

        Args:
            validator: Validator instance
            env_file: Name of the env file (e.g. ".env.dev")
        """
        self.validator = validator or Validator()
        self.env_file = env_file
        self.output_dir = ".vscode"
        self.output_file = "mcp.json"


    def build_mcp_config(self, server_names: List[str]) -> Dict[str, Any]:
        """
        Build .vscode/mcp.json, including a special path for Jupyter.

        For 'jupyter-docker' templates, read the env vars at runtime
        and build a docker run line embedding the real values.
        """
        import shutil, os
        from mcp_setup.validator import MCP_SERVERS

        cfg: Dict[str, Any] = {"servers": {}}

        for name in server_names:
            scfg = MCP_SERVERS.get(name)
            if not scfg:
                print(f"⚠️  Unknown server '{name}' – skipped.")
                continue

            # --- Special path for Jupyter ---
            if scfg.get("template") == "jupyter-docker":
                # ensure required envs are present
                missing = [v for v in scfg["env_vars"] if not os.getenv(v)]
                if missing:
                    print(f"❌  Missing {missing} for Jupyter – skipping.")
                    continue

                url       = os.environ["JUPYTER_URL"]
                token     = os.environ["JUPYTER_TOKEN"]
                notebook  = os.environ["NOTEBOOK_PATH"]

                # 🚀 Conditional networking:
                # - On Linux you can do host networking: container sees localhost directly
                # - On macOS/Windows use port-mapping + host.docker.internal
                docker_args = ["run", "-i", "--rm"]
                if os.getenv("MCP_HOST_NET", "").lower() == "true":
                    # e.g. user exported MCP_HOST_NET=true
                    docker_args += ["--network", "host"]
                else:
                    # default for macOS/Windows
                    docker_args += [
                        "-e", "DOCKER_DEFAULT_PLATFORM=linux/amd64",
                        "-p", "8888:8888"
                    ]

                docker_args += [
                    "-e", f"SERVER_URL={url}",
                    "-e", f"TOKEN={token}",
                    "-e", f"NOTEBOOK_PATH={notebook}",
                    "datalayer/jupyter-mcp-server:latest"
                ]
                entry = { "type": "stdio", "command": "docker", "args": docker_args }
                cfg["servers"][name] = entry
                continue

            # --- Default stdio servers ---
            if scfg["type"] == "stdio":
                cmd = list(scfg["command"])  # copy
                # autodetect uvx / npx etc...
                if cmd[0] == "uvx" and shutil.which("uvx"):
                    cmd[0] = shutil.which("uvx")
                if cmd[0] == "npx" and not shutil.which("npx"):
                    if shutil.which("uvx"):
                        print(f"ℹ️  Replacing missing npx with uvx for {name}")
                        cmd[0] = shutil.which("uvx")
                    else:
                        print(f"❌  Neither 'npx' nor 'uvx' found – {name} will fail.")

                entry = {
                    "type": "stdio",
                    "command": cmd[0],
                }
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
                    print(f"⚠️  No URL for '{name}' – skipped.")
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

        with open(output_path, "w") as f:
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
