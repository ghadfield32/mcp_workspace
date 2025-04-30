# MCP Setup Tool

This repository provides a CLI to scaffold and configure **Model Context Protocol (MCP)** servers for use in VS Code, including Jupyter, Snowflake, Code Executor, and more.

---

## Prerequisites

- **Python 3.10+** and `pip`
- **Node.js & npm** (required to build the Code Executor module)
- **Docker** (for the Jupyter MCP server)
- **JupyterLab** with `ipykernel` and real‑time collaboration:
  ```bash
  pip install jupyterlab==4.4.1 jupyter‑collaboration==4.0.2 ipykernel
  ```
- (Optional) **uvx** CLI for Gitingest-MCP:
  ```bash
  npm install -g @datalayer/uvx
  ```

---

## Getting Started

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-org/mcp-setup.git
   cd mcp-setup
   ```

2. **Create & activate a Python virtual environment**
   ```bash
   python -m venv .venv
   # macOS/Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install Python dependencies**
   ```bash
   pip install -e .
   ```

4. **Build the Code Executor**
   Navigate into the `mcp_code_executor` subproject, install its Node.js dependencies, and build:
   ```bash
   cd mcp_code_executor
   npm install
   npm run build
   cd ..
   ```

5. **Install `uvx` (for Gitingest‑MCP)**
   ```bash
   npm install -g @datalayer/uvx
   ```

6. **Prepare your environment file**
   - Copy the example and rename:
     ```bash
     # macOS/Linux
     cp .env.example .env.dev
     # Windows
     copy .env.example .env.dev
     ```
   - Edit `.env.dev`, filling in your credentials. **Remove any inline comments** after the `=` to avoid parsing issues.
     ```dotenv
     CODE_STORAGE_DIR=code_executor_storage
     CONDA_ENV_NAME=my_conda_env

     SNOWFLAKE_ACCOUNT=ACCOUNT
     SNOWFLAKE_USER=USER
     ...

     # JupyterLab (macOS/Win): use host.docker.internal
     JUPYTER_URL=http://host.docker.internal:8888
     JUPYTER_TOKEN=abc12345
     NOTEBOOK_PATH=notebooks/demo.ipynb

     # OracleDB
     ORACLE_CONNECTION_STRING=username/password@//host:port/service
     TARGET_SCHEMA=myschema
     ```

7. **Export your Jupyter token**
   ```bash
   # macOS/Linux
   export MY_JUPYTER_TOKEN=abc12345
   # Windows PowerShell
   $Env:MY_JUPYTER_TOKEN = "abc12345"
   ```

8. **Start JupyterLab**
   ```bash
   jupyter lab --port 8888 \
     --IdentityProvider.token $MY_JUPYTER_TOKEN \
     --ip 0.0.0.0
   ```
   - **Linux users** (host networking):
     ```bash
     export MCP_HOST_NET=true
     ```

9. **Run the MCP setup script**
   ```bash
   python setup_mcp.py --env dev
   ```
   - Select which servers to enable
   - Provide any missing credentials when prompted
   - On success, `.vscode/mcp.json` is generated

10. **Verify in VS Code**
    - Open this workspace in VS Code
    - Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> (or <kbd>⌘</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd>)
    - Run **MCP: List Servers** — your configured servers should appear

---

## Troubleshooting

- **403 `'_xsrf' argument missing from POST'`**
  - Ensure `JUPYTER_TOKEN` in `.env.dev` exactly matches the token used to start JupyterLab
  - On Linux set `MCP_HOST_NET=true` before running the setup script

- **Unicode errors loading `.env.dev`**
  - Save the file as UTF‑8 without BOM

- **`uvx` not found**
  - Install globally via `npm install -g @datalayer/uvx`

---

## Next Steps

- Extend `MCP_SERVERS` in `validator.py` to add new servers
- Write automated tests for the setup tool
- Package as a PyPI CLI entry point for easy installation

