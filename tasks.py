"""
# tasks.py

This file contains Invoke tasks for automating various setup and development tasks.
"""
import os
import sys
import shutil
import subprocess    # ← new
import time          # ← new
from invoke import task, UnexpectedExit
import json

# Cross-platform Python / venv paths
PYTHON = sys.executable
VENV = ".venv"
WIN = os.name == "nt"  # Added WIN constant for platform checks
if WIN:  # Windows
    VENV_PYTHON = os.path.join(VENV, "Scripts", "python.exe")
else:  # Unix/Linux/MacOS
    VENV_PYTHON = os.path.join(VENV, "bin", "python")

# Configuration
ENV_FILES = {
    "dev": ".env.dev",
    "stage": ".env.stage",
    "prod": ".env.prod",
}
NPM = "npm"
UVX = "@datalayer/uvx"
JUPYTER_PORT = "8888"

# 1. Bootstrap Python venv & install Python deps
@task
def setup_py(c, venv=".venv"):
    """
    Provision the Python environment with **uv**.

    1. If *venv* already exists, re-use it and just `uv sync`.
    2. If not, create it with `uv venv <path>`.
    3. Activate the venv and run `uv sync` to install all deps
       (project in editable-mode is automatic).
    """
    import shlex

    if os.path.isdir(venv):
        print(f"✅  Re-using existing venv: {venv}")
    else:
        c.run(f"uv venv {shlex.quote(venv)}", echo=True)

    # uv provides an activation script we can source inline for *nix shells;
    # on Windows Invoke will fall back to spawning a new cmd.exe run.
    activate = os.path.join(venv, "bin", "activate") if not WIN else None
    cmd_sync = f"uv sync --extra dev"  # include dev extras so lint/tests work

    if activate and os.path.isfile(activate):
        c.run(f". {activate} && {cmd_sync}", shell="/bin/bash", pty=not WIN, echo=True)
    else:  # Windows PowerShell / cmd
        vpy = os.path.join(venv, "Scripts", "python.exe")
        c.run(f"{vpy} -m uv sync --extra dev", echo=True)

# 2. Build the Code Executor sub-project
@task
def setup_js(c):
    c.run("cd mcp_code_executor && npm install && npm run build")

# 3. Install global UVX (if desired)
@task
def setup_uvx(c):
    """
    Attempt to install the (optional) uvx CLI.  If the package is missing
    from npm, print a warning but continue bootstrapping.
    """
    # 1) If uvx already on PATH, nothing to do
    found = shutil.which("uvx")
    if found:
        print(f"✅  `uvx` already installed at: {found}")
        return

    # 2) Attempt to install
    cmd = f"{NPM} install -g {UVX}"
    print(f"[DBG] Running: {cmd}")
    try:
        c.run(cmd, echo=True)
        print("✅  Successfully installed `uvx`.")
    except UnexpectedExit as e:
        stderr = e.result.stderr or ""
        print(f"[DBG] `npm` stderr:\n{stderr}")
        if "E404" in stderr:
            print("⚠️  Skipped uvx: package not found on npm (private?).")
        else:
            print("❌  Failed to install uvx (non-404 error), re-raising.")
            raise

# 4. Copy & prompt for your .env
@task
def init_env(c, env="dev"):
    """
    Copy .env.example → .env.{env} so you can fill in credentials.
    """
    src = ".env.example"
    dst = ENV_FILES.get(env)
    shutil.copy(src, dst)
    print(f"👉  Copied {src} → {dst}. Now edit {dst} with your values.")

# 5. Start JupyterLab (in host or container as needed)
@task
def jupyter(c, env="dev"):
    """
    Launch JupyterLab from the venv, using a clean token from .env.{env}.
    Cuts off any inline '# comment' so the CLI line is never truncated.
    """
    env_path = ENV_FILES.get(env)
    token = None
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8", errors="ignore") as fh:
            for ln in fh:
                if ln.partition("=")[0].strip() == "JUPYTER_TOKEN":
                    token = ln.partition("=")[2].split("#", 1)[0].strip()
                    break

    cmd = (
        f"{VENV_PYTHON} -m jupyter lab "
        f"--port {JUPYTER_PORT} --ip=0.0.0.0 "
        + (f"--NotebookApp.token={token}" if token else "--NotebookApp.token=''")
    )
    c.run(cmd, pty=not WIN, echo=True)

# 6. Run the MCP setup and generate your VS Code config
@task
def mcp(c, env="dev", cursor=False):
    """
    1) Start JupyterLab in the background (so the port and token are live).
    2) Wait a few seconds for it to spin up.
    3) Run setup_mcp.py --env {env} to configure VS Code.
    4) Leave Jupyter running so VS Code can actually connect.
    5) Sync environment file and MCP configuration to parent directory.
    6) If --cursor is True, also sync to .cursor/mcp.json.
    """
    # 1) Read the token from .env
    env_path = ENV_FILES.get(env)
    token = None
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8", errors="ignore") as fh:
            for ln in fh:
                if ln.partition("=")[0].strip() == "JUPYTER_TOKEN":
                    token = ln.partition("=")[2].split("#",1)[0].strip()
                    break

    # 2) Launch JupyterLab
    jupyter_cmd = [
        VENV_PYTHON, "-m", "jupyter", "lab",
        "--port", JUPYTER_PORT, "--ip=0.0.0.0",
        f"--NotebookApp.token={token or ''}"
    ]
    print(f"[INFO] Launching JupyterLab (token={token}) …")
    jproc = subprocess.Popen(jupyter_cmd)

    # 3) Give it time to bind
    time.sleep(5)

    # 4) Run the MCP setup CLI (which writes .vscode/mcp.json in the workspace)
    print(f"[INFO] Running MCP setup with env='{env}' …")
    c.run(f"{VENV_PYTHON} setup_mcp.py --env {env}", echo=True)

    # 5) Compute workspace and parent paths
    root = os.getcwd()                 # e.g. …/mcp_workspace
    parent = os.path.dirname(root)

    # 6) Copy the .env.<env> up one level
    src_env = os.path.join(root, ENV_FILES[env])
    dst_env = os.path.join(parent, ENV_FILES[env])
    copy_cmd = "copy" if WIN else "cp"
    c.run(f"{copy_cmd} {src_env} {dst_env}", echo=True)

    # Read the source config file which is always created by setup_mcp.py
    src_cfg = os.path.join(root, ".vscode", "mcp.json")
    
    # Check if the source config file exists
    if not os.path.exists(src_cfg):
        print(f"⚠️  Warning: Source config file {src_cfg} not found!")
        print(f"    This may happen if setup_mcp.py failed to create it.")
        # Create a minimal default config if the file doesn't exist
        os.makedirs(os.path.dirname(src_cfg), exist_ok=True)
        with open(src_cfg, "w", encoding="utf-8") as f:
            json.dump({"servers": {}}, f)
        print(f"✅  Created minimal default config at {src_cfg}")

    if not cursor:
        # 7) When not in cursor mode, ensure parent .vscode and copy there
        parent_vscode = os.path.join(parent, ".vscode")
        os.makedirs(parent_vscode, exist_ok=True)
        dst_vscode_cfg = os.path.join(parent_vscode, "mcp.json")
        c.run(f"{copy_cmd} {src_cfg} {dst_vscode_cfg}", echo=True)
        print(f"✅  Synced env and VS Code config to {parent_vscode}")
    
    # 8) Handle cursor folder config
    if cursor:
        ws_cursor = os.path.join(root, ".cursor")
        pr_cursor = os.path.join(parent, ".cursor")
        
        print(f"[DEBUG] Creating cursor directories:")
        print(f"  - Workspace cursor dir: {ws_cursor}")
        print(f"  - Parent cursor dir: {pr_cursor}")
        
        try:
            os.makedirs(ws_cursor, exist_ok=True)
            os.makedirs(pr_cursor, exist_ok=True)
            
            # read the vscode config we just wrote
            try:
                with open(src_cfg, "r", encoding="utf-8") as f:
                    vscode_cfg = json.load(f)
                    print(f"[DEBUG] Successfully read source config from {src_cfg}")
            except Exception as e:
                print(f"[ERROR] Failed to read source config: {e}")
                vscode_cfg = {"servers": {}}
                print(f"[DEBUG] Using default empty config instead")

            # build the cursor‐format config (reuse "servers" key)
            cursor_cfg = {
                "servers": vscode_cfg.get("servers", {})
            }

            # write it into each .cursor/mcp.json
            dst_ws_cursor = os.path.join(ws_cursor, "mcp.json")
            dst_pr_cursor = os.path.join(pr_cursor, "mcp.json")
            
            print(f"[DEBUG] Writing cursor configs to:")
            print(f"  - Workspace: {dst_ws_cursor}")
            print(f"  - Parent: {dst_pr_cursor}")
            
            for dst in (dst_ws_cursor, dst_pr_cursor):
                try:
                    with open(dst, "w", encoding="utf-8") as f:
                        json.dump(cursor_cfg, f, indent=2)
                    print(f"[DEBUG] Successfully wrote config to {dst}")
                except Exception as e:
                    print(f"[ERROR] Failed to write to {dst}: {e}")

            print(f"✅  Wrote Cursor config to {os.path.join(parent, '.cursor')}")
            print(f"✅  Synced env file to parent directory")
        except Exception as e:
            print(f"[ERROR] Failed to set up cursor config: {e}")

    print("[INFO] JupyterLab is still running in the background.")
    if cursor:
        print("       You can now open Cursor and use the MCP servers.")
    else:
        print("       You can now open VS Code and do 'MCP: List Servers'.")

# 7. A "meta" task to do it all (minus editing env)
@task(pre=[setup_py, setup_js, setup_uvx, init_env])
def bootstrap(c, env="dev"):
    """
    One-shot: Python deps (via **uv**), JS build, optional uvx, copy .env.

    After this finishes, edit ``.env.{env}`` with credentials
    and run `inv mcp --env={env}`.
    """
    # Normalize & validate the env parameter
    if not env:
        print("[WARN] No --env provided, defaulting to 'dev'")
        env = "dev"
    if env not in ("dev", "stage", "prod"):
        print(f"❌  Invalid env '{env}'. Must be one of dev, stage, prod.")
        sys.exit(1)

    print(f"🚀  Bootstrap complete with uv-managed environment for '{env}'!")
    print(f"👉  Next step: edit `.env.{env}` to fill in your credentials.")
    print(f"👉  Then run: `inv mcp --env={env}`")


