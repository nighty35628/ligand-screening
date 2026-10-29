#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
PYTHON_BIN="${AMADEUS_PYTHON:-$PROJECT_DIR/.venv-allis/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 "$PROJECT_DIR/.venv-allis"
    uv pip install --python "$PROJECT_DIR/.venv-allis/bin/python" -r requirements-allis.txt
  elif command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv "$PROJECT_DIR/.venv-allis"
    "$PROJECT_DIR/.venv-allis/bin/python" -m pip install -r requirements-allis.txt
  else
    echo 'Please install uv or Python 3.12, then run this command again.' >&2
    exit 2
  fi
  PYTHON_BIN="$PROJECT_DIR/.venv-allis/bin/python"
fi
# Install newly introduced engine dependencies for an existing environment too.
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$PYTHON_BIN" -r requirements-allis.txt
else
  "$PYTHON_BIN" -m pip install -r requirements-allis.txt
fi
exec "$PYTHON_BIN" -m amadeus.server "$@"
