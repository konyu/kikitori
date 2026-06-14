#!/usr/bin/env bash
set -euo pipefail

# build-dmg.sh — Kikitori の .app バンドル作成 → DMG 生成
#
# 出力: dist/Kikitori-<version>.dmg
# 依存: swift, create-dmg (brew install create-dmg)

VERSION="${VERSION:-dev}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Kikitori"
BUILD_DIR=".build/release"
APP_BUNDLE="$APP_NAME.app"
DIST_DIR="dist"
DMG_NAME="$APP_NAME-$VERSION.dmg"

echo "=== Build Swift binary ==="
swift build -c release --disable-sandbox

echo "=== Create .app bundle ==="
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# バイナリコピー
cp "$BUILD_DIR/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/"

# Sparkle.framework をバンドル
mkdir -p "$APP_BUNDLE/Contents/Frameworks"
SPARKLE_FW="$BUILD_DIR/Sparkle.framework"
if [ -d "$SPARKLE_FW" ]; then
  cp -R "$SPARKLE_FW" "$APP_BUNDLE/Contents/Frameworks/"
else
  echo "WARNING: Sparkle.framework not found at $SPARKLE_FW"
fi

# アイコンコピー
if [ -f "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/Contents/Resources/icon-idle.png" ]; then
  cp "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/Contents/Resources/icon-idle.png" "$APP_BUNDLE/Contents/Resources/"
fi
if [ -f "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/Contents/Resources/icon-recording.png" ]; then
  cp "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/Contents/Resources/icon-recording.png" "$APP_BUNDLE/Contents/Resources/"
fi

# フォールバック: 直接ソースからアイコンコピー
if [ ! -f "$APP_BUNDLE/Contents/Resources/icon-idle.png" ]; then
  if [ -f "Sources/Kikitori/Resources/icon-idle.png" ]; then
    cp Sources/Kikitori/Resources/icon-idle.png "$APP_BUNDLE/Contents/Resources/"
  fi
fi
if [ ! -f "$APP_BUNDLE/Contents/Resources/icon-recording.png" ]; then
  if [ -f "Sources/Kikitori/Resources/icon-recording.png" ]; then
    cp Sources/Kikitori/Resources/icon-recording.png "$APP_BUNDLE/Contents/Resources/"
  fi
fi

# Info.plist 生成
cat > "$APP_BUNDLE/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>ja</string>
    <key>CFBundleDisplayName</key>
    <string>Kikitori</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.konyu.kikitori</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>SUFeedURL</key>
    <string>https://github.com/konyu/kikitori/releases/latest/download/appcast.xml</string>
    <key>SUEnableInstallerLauncherService</key>
    <true/>
    <key>SUPublicEDKey</key>
    <string>${SU_PUBLIC_ED_KEY:-}</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>音声認識のためにマイクへのアクセスが必要です。</string>
    <key>NSSpeechRecognitionUsageDescription</key>
    <string>音声をテキストに変換するために音声認識を使用します。</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>テキストをペーストするためにアクセシビリティ機能を使用します。</string>
</dict>
</plist>
PLIST

# PkgInfo
echo -n "APPL????" > "$APP_BUNDLE/Contents/PkgInfo"

echo "=== Create DMG ==="
mkdir -p "$DIST_DIR"

if command -v create-dmg &>/dev/null; then
  # create-dmg 使用（より美しいDMG、背景画像・Applicationsシンボリックリンク付き）
  create-dmg \
    --volname "$APP_NAME" \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "$APP_NAME.app" 160 200 \
    --app-drop-link 440 200 \
    --no-internet-enable \
    "$DIST_DIR/$DMG_NAME" \
    "$APP_BUNDLE"
else
  # フォールバック: hdiutil 直接（シンプルDMG）
  echo "create-dmg not found — using hdiutil fallback"
  hdiutil create -volname "$APP_NAME" \
    -srcfolder "$APP_BUNDLE" \
    -ov -format UDZO \
    "$DIST_DIR/$DMG_NAME"
fi

echo "=== Done: $DIST_DIR/$DMG_NAME ==="
ls -lh "$DIST_DIR/$DMG_NAME"

echo "=== Ad-hoc code sign ==="
codesign --sign - --deep --force "$APP_BUNDLE" 2>&1 || echo "WARNING: ad-hoc signing failed (non-fatal)"

echo "=== Generate appcast ==="
if [ -x "$SCRIPT_DIR/generate-appcast.sh" ]; then
  DOWNLOAD_URL="https://github.com/konyu/kikitori/releases/download/v${VERSION}/${DMG_NAME}"
  OUT_FILE="$DIST_DIR/appcast.xml" \
    bash "$SCRIPT_DIR/generate-appcast.sh" "$DIST_DIR/$DMG_NAME" "$VERSION" "$DOWNLOAD_URL"
fi
