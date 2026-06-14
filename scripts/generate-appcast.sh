#!/usr/bin/env bash
set -euo pipefail

# generate-appcast.sh — Sparkle 用 appcast.xml を手動生成
#
# generate_appcast は Apple Code Signing 検証を強制するため、
# Developer ID 署名なしでは利用不可。このスクリプトは自力で appcast.xml を構築する。
#
# Usage:
#   ./scripts/generate-appcast.sh <dmg_path> <version> <download_url>
#
# Env:
#   SPARKLE_PRIVATE_KEY_BASE64  EdDSA 秘密鍵 (base64, generate_keys -x 出力)
#   SPARKLE_PUBLIC_KEY          SUPublicEDKey 値 (オプション)
#
# 出力:
#   <dmg_dir>/appcast.xml

DMG_PATH="${1:?Usage: $0 <dmg_path> <version> <download_url>}"
VERSION="${2:?}"
DOWNLOAD_URL="${3:?}"

DMG_DIR="$(dirname "$DMG_PATH")"
DMG_NAME="$(basename "$DMG_PATH")"
OUT_FILE="${DMG_DIR}/appcast.xml"

SHORT_VERSION="${VERSION}"
BUILD_VERSION="${VERSION}"
MIN_OS="14.0"
ARCH="arm64"

echo "=== Generate appcast.xml ==="
echo "DMG:     $DMG_PATH"
echo "Version: $VERSION"
echo "URL:     $DOWNLOAD_URL"

# --- File size ---
DMG_SIZE=$(stat -f%z "$DMG_PATH" 2>/dev/null || stat -c%s "$DMG_PATH" 2>/dev/null || echo "0")
echo "Size:    $DMG_SIZE bytes"

# --- EdDSA signature ---
# Sparkle の bin/sign_update を使用
TOOLS_DIR="${SPARKLE_BIN_DIR:-$PWD/.build/sparkle-tools}"
if [ ! -x "$TOOLS_DIR/bin/sign_update" ]; then
  echo "Downloading sign_update..."
  SPARKLE_TAG="${SPARKLE_VERSION:-2.9.1}"
  TAR_URL="https://github.com/sparkle-project/Sparkle/releases/download/$SPARKLE_TAG/Sparkle-$SPARKLE_TAG.tar.xz"
  mkdir -p "$TOOLS_DIR"
  curl -fsSL "$TAR_URL" | tar xJ -C "$TOOLS_DIR" --strip-components=1 bin/sign_update 2>/dev/null
  if [ ! -x "$TOOLS_DIR/bin/sign_update" ]; then
    echo "ERROR: sign_update not found"
    exit 1
  fi
fi

ED_SIGNATURE=""
PRIVATE_KEY_CONTENT="${SPARKLE_PRIVATE_KEY_BASE64:-}"

if [ -n "$PRIVATE_KEY_CONTENT" ]; then
  TMP_KEY="$(mktemp)"
  echo -n "$PRIVATE_KEY_CONTENT" > "$TMP_KEY"
  ED_SIGNATURE=$("$TOOLS_DIR/bin/sign_update" --ed-key-file "$TMP_KEY" -p "$DMG_PATH" 2>/dev/null || true)
  rm -f "$TMP_KEY"
  
  if [ -n "$ED_SIGNATURE" ]; then
    echo "EdDSA signature generated"
  else
    echo "WARNING: Failed to generate EdDSA signature"
  fi
else
  echo "WARNING: No EdDSA key — appcast will be unsigned"
fi

# --- Build appcast.xml ---
PUB_DATE=$(date -u +"%a, %d %b %Y %H:%M:%S +0000" 2>/dev/null || date +"%a, %d %b %Y %H:%M:%S +0000")

SIGNATURE_XML=""
if [ -n "$ED_SIGNATURE" ]; then
  SIGNATURE_XML=" sparkle:edSignature=\"$(echo "$ED_SIGNATURE" | xargs)\""
fi

cat > "$OUT_FILE" << XML
<?xml version="1.0" standalone="yes"?>
<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" version="2.0">
    <channel>
        <title>Kikitori</title>
        <item>
            <title>${SHORT_VERSION}</title>
            <pubDate>${PUB_DATE}</pubDate>
            <sparkle:version>${BUILD_VERSION}</sparkle:version>
            <sparkle:shortVersionString>${SHORT_VERSION}</sparkle:shortVersionString>
            <sparkle:minimumSystemVersion>${MIN_OS}</sparkle:minimumSystemVersion>
            <sparkle:hardwareRequirements>${ARCH}</sparkle:hardwareRequirements>
            <enclosure url="${DOWNLOAD_URL}" length="${DMG_SIZE}" type="application/octet-stream"${SIGNATURE_XML}/>
        </item>
    </channel>
</rss>
XML

echo "=== Generated: $OUT_FILE ==="
echo "---"
cat "$OUT_FILE"
echo "---"
