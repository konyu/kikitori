#!/bin/bash
# VoiceToText — ログイン時自動起動 & ログローテーション セットアップ
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/com.voicetotext.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.voicetotext.plist"
NEWSYSLOG_SRC="$SCRIPT_DIR/voicetotext.newsyslog.conf"
NEWSYSLOG_DST="/etc/newsyslog.d/voicetotext.conf"
UID_NUM=$(id -u)

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
