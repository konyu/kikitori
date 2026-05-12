#!/bin/bash
# Kikitori セットアップ — 環境チェック + インストール
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

ok="✅"
warn="⚠️"
fail="❌"

echo "🎤 Kikitori セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. macOS ──
echo "🖥  macOS"
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "?")
echo "   $OS_VER"

# ── 2. Apple Silicon ──
echo ""
echo "🔲 CPU"
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo "   $ok Apple Silicon ($ARCH)"
else
    echo "   $fail $ARCH — mlx-whisper は Apple Silicon 専用"
    exit 1
fi

# ── 3. Python ──
echo ""
echo "🐍 Python"
PYTHON3=$(command -v python3 2>/dev/null || echo "")
if [ -z "$PYTHON3" ]; then
    echo "   $fail 見つかりません"
    exit 1
fi
PY_VER=$("$PYTHON3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "   バージョン: $PY_VER  ($PYTHON3)"
MAJOR=$(echo "$PY_VER" | cut -d. -f1)
MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$MAJOR" -gt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; }; then
    echo "   $ok 3.10+ 対応"
else
    echo "   $fail 3.10 以上が必要"
    exit 1
fi

# ── 4. venv ──
echo ""
echo "📦 仮想環境"
if [ -d "venv" ] && [ -x "venv/bin/python" ]; then
    echo "   $ok 存在"
else
    echo "   作成中..."
    "$PYTHON3" -m venv venv
    echo "   $ok 作成完了"
fi

# ── 5. pip ──
echo ""
echo "📥 pip パッケージ"
MISSING=()
while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    pkg=$(echo "$line" | sed 's/[<>=!~;].*//' | xargs)
    if ! venv/bin/pip show "$pkg" &>/dev/null; then
        MISSING+=("$line")
    fi
done < requirements.txt

if [ ${#MISSING[@]} -eq 0 ]; then
    echo "   $ok 全パッケージインストール済み"
else
    echo "   不足: ${MISSING[*]}"
    venv/bin/pip install -q -r requirements.txt
    echo "   $ok インストール完了"
fi

# ── 6. mlx-whisper ──
echo ""
echo "🤖 Whisper モデル"
CACHE="$HOME/.cache/huggingface/hub"
if [ -d "$CACHE" ]; then
    COUNT=$(find "$CACHE" -name "*.safetensors" -path "*whisper*" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$COUNT" -gt 0 ]; then
        echo "   $ok キャッシュあり（$COUNT ファイル）"
    else
        echo "   $warn 未ダウンロード — 初回起動時に自動取得"
    fi
else
    echo "   $warn HuggingFace キャッシュなし — 初回起動時に自動作成"
fi

# ── 7. Homebrew ──
echo ""
echo "🍺 Homebrew"
if command -v brew &>/dev/null; then
    echo "   $ok $(brew --version | head -1)"
else
    echo "   インストール中..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # パスを通す（Apple Silicon のデフォルト）
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo "   $ok インストール完了"
fi

# ── 8. ffmpeg ──
echo ""
echo "🎬 ffmpeg"
if command -v ffmpeg &>/dev/null; then
    echo "   $ok $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"
else
    echo "   インストール中... (brew install ffmpeg)"
    brew install ffmpeg
    echo "   $ok インストール完了"
fi

# ── 完了 ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎤 セットアップ完了"
echo ""
echo "   起動: ./run.sh"
echo ""
