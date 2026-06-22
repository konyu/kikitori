#!/usr/bin/env bash
set -euo pipefail

# build-dmg.sh — Kikitori の .app バンドル作成 → DMG 生成
#
# 出力: dist/Kikitori-<version>.dmg
# 依存: swift, create-dmg (brew install create-dmg)

VERSION="${VERSION:-dev}"
BUILD_NUMBER="${BUILD_NUMBER:-$VERSION}"
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

# Swift Package Manager が生成するリソースバンドルを Contents/Resources にコピー
# （バンドルルートに置くと ad-hoc 署名時に "unsealed contents" エラーになる）
if [ -d "$BUILD_DIR/${APP_NAME}_Kikitori.bundle" ]; then
  cp -R "$BUILD_DIR/${APP_NAME}_Kikitori.bundle" "$APP_BUNDLE/Contents/Resources/"
  # SPM バンドルはフラット構造の場合があるので、PNG を Contents/Resources 直下にもコピー
  for icon in icon-idle.png icon-recording.png; do
    if [ -f "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/$icon" ]; then
      cp "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/$icon" "$APP_BUNDLE/Contents/Resources/"
    elif [ -f "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/Contents/Resources/$icon" ]; then
      cp "$BUILD_DIR/${APP_NAME}_Kikitori.bundle/Contents/Resources/$icon" "$APP_BUNDLE/Contents/Resources/"
    fi
  done
else
  # SPM バンドルが見つからない場合は直接ソースからコピー
  if [ -f "Sources/Kikitori/Resources/icon-idle.png" ]; then
    cp Sources/Kikitori/Resources/icon-idle.png "$APP_BUNDLE/Contents/Resources/"
  fi
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
    <key>CFBundleLocalizations</key>
    <array>
        <string>ja</string>
        <string>en</string>
    </array>
    <key>CFBundleAllowMixedLocalizations</key>
    <true/>
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
    <string>$BUILD_NUMBER</string>
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
    <key>CFBundleIconFile</key>
    <string>Kikitori.icns</string>
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

# アプリアイコン (.icns) を生成・配置
echo "=== Generate app icon ==="
ICON_SRC="Sources/Kikitori/Resources/icon-idle.png"
ICON_DST="$APP_BUNDLE/Contents/Resources/Kikitori.icns"
if [ -f "$ICON_SRC" ]; then
    if [ -x "$SCRIPT_DIR/generate-icns.sh" ]; then
        "$SCRIPT_DIR/generate-icns.sh" "$ICON_SRC" "$ICON_DST"
    elif [ -f "assets/Kikitori.icns" ]; then
        cp "assets/Kikitori.icns" "$ICON_DST"
    else
        echo "WARNING: no icon generation script or prebuilt icns found"
    fi
else
    echo "WARNING: icon source not found: $ICON_SRC"
fi

echo "=== Code sign ==="
SIGNING_IDENTITY="${CODE_SIGN_IDENTITY:--}"
echo "Using identity: $SIGNING_IDENTITY"
codesign --sign "$SIGNING_IDENTITY" --deep --force "$APP_BUNDLE" 2>&1 || echo "WARNING: signing failed (non-fatal)"

echo "=== Create DMG ==="
mkdir -p "$DIST_DIR"

# DMG背景画像の生成
BG_IMAGE="$DIST_DIR/dmg-bg.png"
if [ -x "$SCRIPT_DIR/generate-dmg-bg.swift" ]; then
    "$SCRIPT_DIR/generate-dmg-bg.swift" "$BG_IMAGE"
fi

if command -v create-dmg &>/dev/null; then
  # create-dmg 使用（より美しいDMG、背景画像・Applicationsシンボリックリンク付き）
  
  CREATE_DMG_ARGS=(
    --volname "$APP_NAME"
    --window-size 600 400
    --icon-size 100
    --icon "$APP_NAME.app" 160 200
    --app-drop-link 440 200
    --no-internet-enable
  )
  
  if [ -f "$BG_IMAGE" ]; then
      CREATE_DMG_ARGS+=(--background "$BG_IMAGE")
  fi

  if [ -f "$ICON_DST" ]; then
      CREATE_DMG_ARGS+=(--volicon "$ICON_DST")
  fi

  create-dmg "${CREATE_DMG_ARGS[@]}" "$DIST_DIR/$DMG_NAME" "$APP_BUNDLE"
else
  # フォールバック: hdiutil 直接（シンプルDMG + Applicationsリンク）
  echo "create-dmg not found — using hdiutil fallback with Applications link"
  DMG_ROOT="$DIST_DIR/dmg_root"
  mkdir -p "$DMG_ROOT"
  cp -R "$APP_BUNDLE" "$DMG_ROOT/"
  ln -s /Applications "$DMG_ROOT/Applications"
  
  hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_ROOT" \
    -ov -format UDZO \
    "$DIST_DIR/$DMG_NAME"
    
  rm -rf "$DMG_ROOT"
fi

echo "=== Done: $DIST_DIR/$DMG_NAME ==="
ls -lh "$DIST_DIR/$DMG_NAME"

echo "=== Generate appcast ==="
if [ -x "$SCRIPT_DIR/generate-appcast.sh" ]; then
  DOWNLOAD_URL="https://github.com/konyu/kikitori/releases/download/v${VERSION}/${DMG_NAME}"
  OUT_FILE="$DIST_DIR/appcast.xml" \
    bash "$SCRIPT_DIR/generate-appcast.sh" "$DIST_DIR/$DMG_NAME" "$VERSION" "$DOWNLOAD_URL" "$BUILD_NUMBER"
fi
