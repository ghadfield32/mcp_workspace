```markdown
# MCP Setup Tool

A one-command bootstrap + CLI that scaffolds **Model Context Protocol (MCP)** servers
for VS Code – Jupyter, Snowflake, Code Executor, OracleDB, Gitingest-MCP, and more.
A FastAPI management service is also included for programmatic control.

---

## Prerequisites (3 things)

| What | Why |
|------|-----|
| **Python 3.12+** + [`uv`](https://github.com/astral-sh/uv) | `uv` handles virtual-env creation **and** dependency sync in one shot. <br>Install once via `pipx install uv` or `pip install -U uv`. |
| **Node.js & npm** | Builds the *Code Executor* sub-project. |
| **Docker** | Runs the Jupyter MCP server in a container. |

> **Optional**:  
> • `npm i -g @datalayer/uvx` if you want the **Gitingest-MCP** server.  
> • `pip install jupyterlab==4.4.1 jupyter-collaboration==4.0.2 ipykernel` if you
>   plan to run *local* JupyterLab instead of the container image.

---

## Quick start — 3 commands

```bash
git clone https://github.com/your-org/mcp-setup.git
cd mcp-setup

inv bootstrap --env=dev   # ① create venv with uv, ② npm build, ③ copy .env.dev and update with your api keys
inv mcp       --env=dev   # ① launch Jupyter in bg, ② interactive server wizard
```

Open VS Code → Press ctrl + shift + P → **MCP: List Servers** – you should see the servers list stopped, click them and press enter to start them. Then open the chat window and they will show in Agent mode (of vscode or cursor mode).

---

## What each task does

| Task | What happens internally |
|------|-------------------------|
| **`inv bootstrap --env=<e>`** | *Python side* • `uv venv .venv` (or reuse). • `uv sync --extra dev` (installs deps **and** this repo in editable mode).<br>*Node side* • `npm install && npm run build` inside `mcp_code_executor/`.<br>*Quality-of-life* • Installs `uvx` (if npm available). • Copies `.env.example` → `.env.<e>`. |
| **`inv mcp --env=<e>`** | *Background* • Starts JupyterLab on :8888 with the token from `.env.<e>`.<br>*Wizard* • Lets you pick servers, prompts for any missing env vars, validates, and writes `.vscode/mcp.json` with smart Docker/stdio/SSE entries.<br>*After* • Leaves Jupyter running so VS Code can connect immediately. |

---

## Minimal manual edits

1. **Edit `.env.<env>`** – fill in credentials (Snowflake, Oracle, etc.).  
   *Inline comments after `=` will be ignored.*
2. (Optional) **Set `MCP_HOST_NET=true`** on Linux if port 8888 is already in use
   and you prefer `--network host` for the Jupyter container.

Everything else is automated by the Invoke tasks.

---

## Troubleshooting FAQ

| Symptom | Fix |
|---------|-----|
| `docker: failed to bind port 8888` | Windows/macOS: the container skips `-p 8888:8888` automatically and talks to `host.docker.internal:8888`. Linux: export `MCP_HOST_NET=true`. |
| 403 `'_xsrf' argument missing` | `JUPYTER_TOKEN` in `.env.<env>` must *exactly* match the one JupyterLab started with. |
| `uvx` not found when enabling Gitingest-MCP | `npm i -g @datalayer/uvx` |
| Unicode errors reading `.env` | Save file as **UTF-8 (without BOM)**. |

---

## Next steps

* Extend **`MCP_SERVERS`** in `mcp_setup/validator.py` to add more back-ends.  
* Ship automated tests for validation / generation.  
* Publish to PyPI so users can simply run    
  `pipx install mcp-server-setup && mcp-setup --env dev`.
```

---

### Why the old steps are gone

| Old README step | Needed now? | Why |
|-----------------|-------------|-----|
| `python -m venv …` | **No** | `uv venv` inside `inv bootstrap` handles it. |
| `pip install -e .` | **No** | `uv sync` automatically installs the project in editable mode. |
| Manual JupyterLab launch | **No** | `inv mcp` spins Jupyter up in the background, waits 5 s, then runs the generator. |
| `npm install -g @datalayer/uvx` | **Optional** | Only required if you enable the Gitingest-MCP server. |
| FastAPI / Uvicorn API section | **Optional** | Start it only if you want the HTTP control plane; the CLI works fine without it. |

Enjoy the single-command setup!