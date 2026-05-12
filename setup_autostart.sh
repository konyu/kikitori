#!/bin/bash
# VoiceToText — ログイン時自動起動 & ログローテーション セットアップ
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python"
PLIST_SRC="$SCRIPT_DIR/com.voicetotext.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.voicetotext.plist"
NEWSYSLOG_SRC="$SCRIPT_DIR/voicetotext.newsyslog.conf"
NEWSYSLOG_DST="/etc/newsyslog.d/voicetotext.conf"
UID_NUM=$(id -u)

# ── 0. アクセシビリティ権限の事前チェック ──
echo "🔍 アクセシビリティ権限を確認中..."
echo ""

# Python バイナリのパス（Launch Agent 経由で実行される実体）
PYTHON_REAL=$(cd "$SCRIPT_DIR" && "$PYTHON" -c 'import sys; print(sys.executable)' 2>/dev/null || echo "$PYTHON")

# 権限データベースから確認（Python バイナリが登録されているか）
PERM_DB="/Library/Application Support/com.apple.TCC/TCC.db"
if [ -f "$PERM_DB" ]; then
    HAS_ACCESS=$(sudo sqlite3 "$PERM_DB" "SELECT count(*) FROM access WHERE service='kTCCServiceAccessibility' AND client LIKE '%python%';" 2>/dev/null || echo "0")
else
    HAS_ACCESS="unknown"
fi

echo "   Python パス: $PYTHON_REAL"
echo ""

if [ "$HAS_ACCESS" = "unknown" ] || [ "$HAS_ACCESS" -eq 0 ] 2>/dev/null; then
    echo "⚠️  重要: Launch Agent 経由ではアクセシビリティ権限が不足しています"
    echo ""
    echo "   以下の Python バイナリをアクセシビリティ設定に追加してください:"
    echo ""
    echo "     $PYTHON_REAL"
    echo ""
    echo "   手順:"
    echo "     1. システム設定 → プライバシーとセキュリティ → アクセシビリティ"
    echo "     2. 解錠して「+」をクリック"
    echo "     3. Cmd+Shift+G で '$PYTHON_REAL' を入力"
    echo "     4. 追加後、✅ が付いていることを確認"
    echo ""
    read -p "   設定したら Enter を押してください... "
    echo ""
fi

# ── 1. plist のパスを置換してインストール ──
echo "📋 Launch Agent をインストール..."
mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__SCRIPT_DIR__|$SCRIPT_DIR|g" "$PLIST_SRC" > "$PLIST_DST"

# 既存の起動があれば再読み込み
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"
echo "   ✅ $PLIST_DST"

# ── 2. newsyslog のインストール ──
echo ""
echo "📝 ログローテーション設定をインストール..."
sudo bash -c "
  mkdir -p /etc/newsyslog.d
  sed 's/501/$UID_NUM/g' '$NEWSYSLOG_SRC' > '$NEWSYSLOG_DST'
  newsyslog -C -f '$NEWSYSLOG_DST'
"
echo "   ✅ $NEWSYSLOG_DST"

# ── 3. 確認 ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ セットアップ完了"
echo ""
echo "反映確認:"
echo "  launchctl list | grep voicetotext"
echo "  tail -f /tmp/voicetotext.log"
echo ""
echo "停止したい場合:"
echo "  launchctl unload $PLIST_DST"
echo ""
echo "ログローテーション確認:"
echo "  newsyslog -nv -f $NEWSYSLOG_DST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
