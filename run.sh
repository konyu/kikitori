#!/bin/bash
# VoiceToText メニューバーアプリ起動スクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
PYTHON="${VENV_DIR}/bin/python"

cd "$SCRIPT_DIR"

# 仮想環境の存在確認
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ 仮想環境が見つかりません"
    echo "   まず以下を実行してください:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Python 実行ファイルの確認
if [ ! -x "$PYTHON" ]; then
    echo "❌ Python 実行ファイルが見つかりません: $PYTHON"
    exit 1
fi

# アクセシビリティ権限の確認
PERM_CHECK=$(osascript -e '
    tell application "System Events"
        return UI elements enabled
    end tell
' 2>/dev/null || echo "unknown")

if [ "$PERM_CHECK" != "true" ]; then
    echo "⚠️  アクセシビリティ権限が無効です"
    echo "   ホットキーを使うには以下を実行してください:"
    echo "   システム設定 → プライバシーとセキュリティ → アクセシビリティ"
    echo "   → ターミナル.app（または iTerm.app）に ✅"
    echo ""
    echo "   アプリ起動後、権限ダイアログが表示される場合もあります"
    echo ""
fi

echo "🎤 VoiceToText を起動します..."
echo "   終了: メニューバー → 🎤 → 終了"
echo ""

exec "$PYTHON" menu_bar_app.py "$@"
