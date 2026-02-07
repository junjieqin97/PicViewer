#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TS_DIR="$ROOT_DIR/src/pic_viewer/ui/resources/i18n"
OUT_DIR="${1:-$TS_DIR}"

if [[ ! -d "$TS_DIR" ]]; then
  echo "TS 目录不存在: $TS_DIR"
  exit 1
fi

mkdir -p "$OUT_DIR"

shopt -s nullglob
ts_files=("$TS_DIR"/picviewer_*.ts)
if [[ ${#ts_files[@]} -eq 0 ]]; then
  echo "未找到 TS 文件: $TS_DIR/picviewer_*.ts"
  exit 1
fi

for ts in "${ts_files[@]}"; do
  lang="$(basename "$ts" .ts)"
  qm="$OUT_DIR/$lang.qm"
  echo "生成 $qm"
  lrelease "$ts" -qm "$qm"
done

echo "完成。"
