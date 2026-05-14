#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${1:-}"

if [[ -n "$OUT_DIR" ]]; then
  python "$ROOT_DIR/scripts/i18n/build_qm.py" --out-dir "$OUT_DIR"
else
  python "$ROOT_DIR/scripts/i18n/build_qm.py"
fi
