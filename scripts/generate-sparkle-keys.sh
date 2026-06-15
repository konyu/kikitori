#!/usr/bin/env bash
set -euo pipefail

# generate-sparkle-keys.sh — Sparkle 用 EdDSA (Ed25519) キーペアを生成
#
# macOS Keychain に秘密鍵を保存し、CI 用に秘密鍵ファイルをエクスポート。
# 自動ダウンロードされるため、Sparkle のインストール不要。
#
# 出力ファイル:
#   .config/sparkle/private.pem   秘密鍵 (CI Secret 用 / Git にコミットしない)
#   .config/sparkle/public.pem    公開鍵 (base64 1行)
#
# 公開鍵はビルド時の Info.plist SUPublicEDKey に設定する。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
KEYS_DIR="${PROJECT_DIR}/.config/sparkle"
SPARKLE_VERSION="${SPARKLE_VERSION:-2.9.1}"

echo "=== Generate Sparkle EdDSA key pair ==="
mkdir -p "$KEYS_DIR"

PRIVATE_KEY="$KEYS_DIR/private.pem"
PUBLIC_KEY="$KEYS_DIR/public.pem"

# --- Download generate_keys from Sparkle ---
TOOLS_DIR="$PROJECT_DIR/.build/sparkle-tools"
if [ ! -x "$TOOLS_DIR/bin/generate_keys" ]; then
  echo "Downloading Sparkle $SPARKLE_VERSION tools..."
  TAR_URL="https://github.com/sparkle-project/Sparkle/releases/download/$SPARKLE_VERSION/Sparkle-$SPARKLE_VERSION.tar.xz"
  mkdir -p "$TOOLS_DIR"
  curl -fsSL "$TAR_URL" | tar xJ -C "$TOOLS_DIR" --strip-components=1 \
    bin/generate_keys 2>/dev/null
  if [ ! -x "$TOOLS_DIR/bin/generate_keys" ]; then
    echo "ERROR: generate_keys not found after extraction"
    ls -la "$TOOLS_DIR/bin/" 2>/dev/null || echo "(bin/ not found)"
    exit 1
  fi
fi

GEN_KEYS="$TOOLS_DIR/bin/generate_keys"

# --- Check if key already in Keychain ---
echo "Checking for existing Sparkle key in Keychain..."
EXISTING_PUB=$("$GEN_KEYS" -p 2>/dev/null) || true

if [ -n "$EXISTING_PUB" ]; then
  echo "Existing Sparkle key found in Keychain."
  echo "Public key: $EXISTING_PUB"
  echo ""
  
  if [ ! -f "$PRIVATE_KEY" ]; then
    echo "Exporting private key to $PRIVATE_KEY..."
    "$GEN_KEYS" -x "$PRIVATE_KEY"
    echo "Private key exported."
  else
    echo "Private key file already exists: $PRIVATE_KEY"
  fi
  
  # Save public key
  echo -n "$EXISTING_PUB" > "$PUBLIC_KEY"
else
  echo "No existing key. Generating new EdDSA key pair..."
  echo "You may be prompted to allow Keychain access."
  echo ""
  
  # generate_keys creates key in Keychain and prints info
  "$GEN_KEYS" 2>&1 | tee /tmp/sparkle_gen_output.txt
  EXISTING_PUB=$("$GEN_KEYS" -p 2>/dev/null)
  
  if [ -z "$EXISTING_PUB" ]; then
    echo "ERROR: Failed to generate or retrieve key"
    exit 1
  fi
  
  echo "Exporting private key..."
  "$GEN_KEYS" -x "$PRIVATE_KEY"
  
  echo -n "$EXISTING_PUB" > "$PUBLIC_KEY"
fi

echo ""
echo "=== Keys ready ==="
echo "Private: $PRIVATE_KEY"
echo "Public:  $PUBLIC_KEY"
echo ""

PUBLIC_BASE64="$EXISTING_PUB"
echo "──────────────────────────────────────────"
echo "SUPublicEDKey (for Info.plist / env var):"
echo "$PUBLIC_BASE64"
echo ""

# CI 用 base64 秘密鍵
PRIVATE_BASE64=$(base64 -i "$PRIVATE_KEY" | tr -d '\n')
echo "SPARKLE_PRIVATE_KEY_BASE64 (for GitHub Secrets):"
echo "$PRIVATE_BASE64"
echo "──────────────────────────────────────────"
echo ""

echo "=== Next steps ==="
echo "1. GitHub → repo Settings → Secrets and variables → Actions"
echo "   → New repository secret"
echo "     Name:  SPARKLE_PRIVATE_KEY_BASE64"
echo "     Value: <上記 base64 値>"
echo ""
echo "2. ローカルビルド時:"
echo "   export SU_PUBLIC_ED_KEY='$PUBLIC_BASE64'"
echo "   bash scripts/build-dmg.sh"
echo ""
echo "3. CI: GitHub Actions が自動で秘密鍵をデコードして署名"
