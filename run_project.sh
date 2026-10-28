#!/usr/bin/env bash
# Unified benchmark; historical model commands remain available under `models`.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
if [[ "${1:-}" == "models" ]]; then
  shift
  exec "$PROJECT_DIR/run_allis.sh" "$@"
fi
PYTHON_BIN="${ALLIS_PYTHON:-$PROJECT_DIR/.venv-allis/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  "$PROJECT_DIR/run_allis.sh" check >/dev/null
fi
if [[ $# -eq 0 ]]; then set -- run --mode cached; fi
exec "$PYTHON_BIN" -m allis_benchmark "$@"
