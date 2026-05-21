#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="$ROOT_DIR/src/pic_viewer"
TS_DIR="$SRC_DIR/ui/resources/i18n"

mkdir -p "$TS_DIR"

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
SHADOW_SRC_DIR="$TMP_ROOT/src/pic_viewer"
SHADOW_TS_DIR="$SHADOW_SRC_DIR/ui/resources/i18n"

mkdir -p "$SHADOW_TS_DIR"
cp "$TS_DIR"/picviewer_*.ts "$SHADOW_TS_DIR"/

SOURCES=()
while IFS= read -r file; do
  relative_path="${file#"$SRC_DIR"/}"
  shadow_file="$SHADOW_SRC_DIR/$relative_path"
  mkdir -p "$(dirname "$shadow_file")"
  perl -pe 's/\bself\._tr\(/self.tr(/g; s/\b_tr\(/tr(/g' "$file" > "$shadow_file"
  SOURCES+=("$shadow_file")
done < <(find "$SRC_DIR" -name "*.py" -type f | sort)

if [[ ${#SOURCES[@]} -eq 0 ]]; then
  echo "未找到可提取翻译文本的 Python 文件。"
  exit 1
fi

echo "更新 TS 文件到: $TS_DIR"
pyside2-lupdate \
  -noobsolete \
  "${SOURCES[@]}" \
  -ts \
  "$SHADOW_TS_DIR/picviewer_zh_CN.ts" \
  "$SHADOW_TS_DIR/picviewer_en.ts"

cp "$SHADOW_TS_DIR/picviewer_zh_CN.ts" "$TS_DIR/picviewer_zh_CN.ts"
cp "$SHADOW_TS_DIR/picviewer_en.ts" "$TS_DIR/picviewer_en.ts"

echo "完成。"
