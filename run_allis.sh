#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
if [[ -n "${ALLIS_PYTHON:-}" ]]; then
  PYTHON_BIN="$ALLIS_PYTHON"
else
  PYTHON_BIN="$PROJECT_DIR/.venv-allis/bin/python"
  if [[ ! -x "$PYTHON_BIN" ]]; then
    if command -v uv >/dev/null 2>&1; then
      uv venv --python 3.12 "$PROJECT_DIR/.venv-allis"
      uv pip install --python "$PYTHON_BIN" -r "$PROJECT_DIR/requirements-allis.txt"
    else
      if ! command -v python3.12 >/dev/null 2>&1; then
        echo 'Please install Python 3.12 or uv, or set ALLIS_PYTHON to a configured Python 3.12 interpreter.' >&2
        exit 2
      fi
      python3.12 -m venv "$PROJECT_DIR/.venv-allis"
      "$PYTHON_BIN" -m pip install -r "$PROJECT_DIR/requirements-allis.txt"
    fi
  fi
fi
if [[ $# -eq 0 ]]; then
  set -- run --mode cached
fi
exec "$PYTHON_BIN" -m allis_delivery "$@"
