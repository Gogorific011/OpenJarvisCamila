$ErrorActionPreference = 'Stop'
if (-not (Test-Path .venv)) { uv venv }
uv pip install -r requirements.txt
uv run python server.py
