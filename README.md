# MCP Setup Tool

A one-command bootstrap + CLI that scaffolds **Model Context Protocol (MCP)** servers for VS Code – Jupyter, Snowflake, Code Executor, OracleDB, Gitingest-MCP, and more. A FastAPI management service is also included for programmatic control.

---

## Prerequisites (3 things)

| What | Why |
|------|-----|
| **Python 3.12+** + [`uv`](https://github.com/astral-sh/uv) | `uv` handles virtual-env creation **and** dependency sync in one shot.<br>Install once via `pipx install uv` or `pip install -U uv`. |
| **Node.js & npm** | Builds the *Code Executor* sub-project. |
| **Docker** | Runs the Jupyter MCP server in a container. |

> **Optional**:  
> • `npm i -g @datalayer/uvx` if you want the **Gitingest-MCP** server.  
> • `pip install jupyterlab==4.4.1 jupyter-collaboration==4.0.2 ipykernel` if you plan to run *local* JupyterLab instead of the container image.

---

## Quick start — 3 commands

```bash
git clone https://github.com/your-org/mcp-setup.git
cd mcp-setup/mcp_workspace

inv bootstrap --env=dev   # ① create venv with uv, ② npm build, ③ copy .env.dev and update with your API keys
inv mcp       --env=dev   # ① launch Jupyter in bg, ② interactive server wizard
cd ..                  # sync .env and .vscode/mcp.json to repo root
```

Open VS Code → Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> → **MCP: List Servers** – you should see your servers. Select one to start it, then open the chat/agent view.

---

## What each task does

| Task                           | What happens internally                                                                                                                  |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| **`inv bootstrap --env=<e>`**  | • **Python**: `uv venv .venv` (or reuse) & `uv sync --extra dev` (installs deps + editable package).<br>• **Node**: `npm install && npm run build` in `mcp_code_executor/`.<br>• Installs `uvx` if available.<br>• Copies `.env.example` → `.env.<e>`. |
| **`inv mcp --env=<e>`**        | • **Background**: Starts JupyterLab on :8888 with token from `.env.<e>`, waits 5 s.<br>• **Wizard**: Interactive server picker, prompts for missing env vars, validates, writes `.vscode/mcp.json` (Docker/stdio/SSE aware).<br>• **Sync**: Copies `.env.<e>` and `.vscode/mcp.json` up to the repo root. |  

---

## Minimal manual edits

1. **Edit `.env.<env>`** – fill in your credentials (`Snowflake`, `Oracle`, etc.).  
   Inline comments after `=` are ignored.
2. (Optional) **Set `MCP_HOST_NET=true`** on Linux if port 8888 is in use and you prefer `--network host` for Jupyter.

Everything else is automated by the Invoke tasks.

---

## Troubleshooting FAQ

| Symptom                                   | Fix                                                                                           |
|-------------------------------------------|-----------------------------------------------------------------------------------------------|
| `docker: failed to bind port 8888`        | On Windows/macOS the container skips `-p 8888:8888` and uses `host.docker.internal:8888`.<br>On Linux set `MCP_HOST_NET=true`. |
| 403 `'_xsrf' argument missing`            | Ensure `JUPYTER_TOKEN` in `.env.<env>` exactly matches JupyterLab’s token.                     |
| `uvx` not found when enabling Gitingest-MCP | Install with `npm i -g @datalayer/uvx`.                                                           |
| Unicode errors reading `.env`             | Save the file as **UTF-8 (without BOM)**.                                                      |

---

## Next steps

- Extend **`MCP_SERVERS`** in `mcp_setup/validator.py` to add more back‑ends.
- Ship automated tests for validation/generation.
- Publish to PyPI so users can run `pipx install mcp-server-setup && mcp-setup --env dev`.

---

### Why the old steps are gone

| Old README step                   | Needed now? | Why                                                                                              |
|-----------------------------------|-------------|--------------------------------------------------------------------------------------------------|
| `python -m venv …`                | No          | `uv venv` inside `inv bootstrap` handles it.                                                      |
| `pip install -e .`                | No          | `uv sync` installs the project in editable mode automatically.                                   |
| Manual JupyterLab launch          | No          | `inv mcp` spins Jupyter up in the background and runs the generator.                              |
| `npm install -g @datalayer/uvx`   | Optional    | Only needed to enable the Gitingest‑MCP server.                                                  |
| FastAPI/Uvicorn API section       | Optional    | Only if you want an HTTP control plane; the CLI works without it.                                |

Enjoy the single‑command setup!  

