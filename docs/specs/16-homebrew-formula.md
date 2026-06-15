# 16 — Homebrew Formula

## 目的
ユーザーが `brew install` で簡単にインストールできるようにする。

## Python 版参照
`/opt/homebrew/Library/Taps/konyu/homebrew-kikitori/Formula/kikitori.rb`:
```ruby
class Kikitori < Formula
  desc "macOS menu bar speech-to-text tool"
  homepage "https://github.com/konyu/kikitori"
  version "0.5.0"
  
  depends_on macos: :sonoma  # macOS 14+
  depends_on "python@3.14"
  
  resource "..." do ... end  # pip 依存
  
  def install
    # venv 作成 → pip install → スクリプト配置
  end
  
  service do
    run [opt_bin/"kikitori"]
    keep_alive true
    log_path var/"log/kikitori.log"
  end
end
```

## Swift 版 Formula 仕様

### ビルド方法
`swift build -c release` でバイナリ生成。依存が少ない（システムフレームワークのみ）。

### Formula 構造
```ruby
class Kikitori < Formula
  desc "macOS menu bar speech-to-text tool using Apple Speech Framework"
  homepage "https://github.com/konyu/kikitori"
  version "0.7.0"
  license "MIT"
  
  depends_on macos: :sequoia  # macOS 15+（Swift 6 要件）
  depends_on xcode: "16.0"    # Swift 6.0 コンパイラ
  
  # ソース: GitHub リリース tarball
  url "https://github.com/konyu/kikitori/archive/refs/tags/v0.7.0.tar.gz"
  sha256 "..." # 自動計算
  
  def install
    system "swift", "build", "-c", "release",
           "--disable-sandbox"
    
    bin.install ".build/release/Kikitori" => "kikitori"
  end
  
  def post_install
    # アクセシビリティ権限ガイド表示
    ohai "System Preferences → Privacy & Security → Accessibility"
    ohai "Add Kikitori and enable it."
  end
  
  service do
    run [opt_bin/"kikitori"]
    keep_alive true
    log_path var/"log/kikitori.log"
    error_log_path var/"log/kikitori.error.log"
  end
  
  test do
    system bin/"kikitori", "--version"
  end
end
```

### GitHub Actions 自動ビルド
`.github/workflows/release.yml`:
```yaml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: macos-15  # Apple Silicon ランナー
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: swift build -c release
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: .build/release/Kikitori
      - name: Update Homebrew Formula
        # Formula の url/sha256 を自動更新
```

### Bottle 対応
- Apple Silicon ネイティブバイナリなので bottle 不要
- または `brew bottle` で bottle 生成可能

### Info.plist 要件
```xml
<key>LSUIElement</key>
<true/>  <!-- メニューバー専用、Dock非表示 -->
<key>NSMicrophoneUsageDescription</key>
<string>Kikitori needs microphone access for speech recognition.</string>
```

### 権限要件
- マイク権限（NSMicrophoneUsageDescription）
- アクセシビリティ権限（ユーザー手動付与）
- エンタイトルメント不要（サンドボックス非対応のため）

### 注意点
- `swift build --disable-sandbox` が必要（Homebrew のサンドボックス環境ではネットワークアクセス不可）
- リリース前に `swift test` 全通過確認
- `--help` / `--version` フラグ必須（test ブロック用）
