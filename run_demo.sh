#!/bin/sh
# Static existing-results demo. No fitting or dependency installation.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PORT=${ALLIS_DEMO_PORT:-8765}
DEMO_DIR="$ROOT/demo/final"
if [ ! -f "$DEMO_DIR/index.html" ]; then DEMO_DIR="$ROOT/demo"; fi
printf '配体优选演示：http://127.0.0.1:%s\n按 Ctrl+C 停止。也可直接打开 demo/final/index.html 离线查看。\n' "$PORT"
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DEMO_DIR"
