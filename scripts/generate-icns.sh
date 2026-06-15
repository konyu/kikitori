#!/usr/bin/env bash
# generate-icns.sh — PNG から macOS .icns アイコンを生成
#
# 使用例:
#   ./scripts/generate-icns.sh [input.png] [output.icns]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT_PNG="${1:-$ROOT_DIR/Sources/Kikitori/Resources/icon-idle.png}"
OUTPUT_ICNS="${2:-$ROOT_DIR/assets/Kikitori.icns}"

if [ ! -f "$INPUT_PNG" ]; then
    echo "ERROR: input PNG not found: $INPUT_PNG"
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT_ICNS")"

ICONSET_DIR="$(mktemp -d)/Kikitori.iconset"
mkdir -p "$ICONSET_DIR"

# macOS アプリアイコンに必要な解像度を生成
SIZES=(16 32 64 128 256 512)
for size in "${SIZES[@]}"; do
    sips -z "$size" "$size" "$INPUT_PNG" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null 2>&1
    sips -z "$((size * 2))" "$((size * 2))" "$INPUT_PNG" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null 2>&1
done

# 最大 1024x1024 も明示的に追加（Retina 512px2x 相当）
sips -z 1024 1024 "$INPUT_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null 2>&1

iconutil -c icns "$ICONSET_DIR" -o "$OUTPUT_ICNS"
rm -rf "$ICONSET_DIR"

echo "Generated: $OUTPUT_ICNS"
