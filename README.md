# 🎤 Kikitori

macOS 向け音声認識入力ツール。ホットキー押下中にマイク入力を録音し、解放時に Apple Silicon 最適化された Whisper モデルが音声をテキストに変換、クリップボード経由で自動ペーストします。

## 特徴

- **Apple Silicon 最適化**: `mlx-whisper` による高速な音声認識（M1/M2/M3/M4）
- **ホットキー操作**: 設定可能なホットキー（デフォルト: Option） — 押下中録音、解放で即時テキスト化
- **メニューバー常駐**: PySide6 による macOS メニューバーアプリ（Homebrew またはターミナル実行）
- **設定ファイル対応**: ホットキー・言語・プロンプトを JSON ファイルでカスタマイズ可能
- **最大60秒録音**: 長時間録音の自動区切り機能

## 動作環境

- Apple Silicon Mac（M1/M2/M3/M4）
- Python 3.14（Homebrew インストール時は自動）
- macOS 14（Sonoma）以上推奨

## 必要な権限

| 権限 | 設定場所 | 用途 |
|------|---------|------|
| マイク | システム設定 → プライバシーとセキュリティ → マイク | 音声入力 |
| アクセシビリティ | システム設定 → プライバシーとセキュリティ → アクセシビリティ | グローバルホットキー監視・自動ペースト |

## インストール

### Homebrew でインストール（推奨）

Formula は [`konyu/homebrew-kikitori`](https://github.com/konyu/homebrew-kikitori) で管理されています。

```bash
# 1. タップを追加
brew tap konyu/kikitori

# 2. インストール（Python 3.14・ffmpeg・すべての依存関係を自動解決）
brew install kikitori

# 3. 起動（メニューバーにアイコンが表示されます）
kikitori

# オプション: ログイン時に自動起動
brew services start konyu/kikitori/kikitori
```

### 手動インストール（開発者向け）

```bash
# リポジトリをクローン
git clone https://github.com/konyu/kikitori.git
cd kikitori

# 仮想環境の作成と有効化（Python 3.14 推奨）
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt

# ffmpeg のインストール（Homebrew 経由）
brew install ffmpeg
```

## 使い方

### メニューバーアプリとして実行（推奨）

```bash
./run.sh
```

メニューバーに 🎤 アイコンが表示されます。デフォルトでは **Option キー** がホットキーです。

- **Option 押下中**: 録音開始（🔴 アイコンに変化）
- **Option 解放**: 録音停止 → 音声認識 → 自動ペースト

### PySide6 版（画面中央下にオーバーレイUI）

AQUA VOICE のような、録音中に画面中央下に波形アニメーションと「音声入力中...」の
オーバーレイを表示するバージョンです。マウスクリックは下のアプリに透過します。

```bash
source venv/bin/activate
python pyside_main.py
```

特徴:
- **フレームレス・常時最前面**のオーバーレイウィンドウ
- **マウスクリック透過**（後ろのアプリが操作可能）
- **リアルタイム波形アニメーション**（30本のバーが音声の大きさに応じて変動）
- **PySide6 QSystemTrayIcon** でメニューバー常駐

### コマンドラインから直接実行

```bash
source venv/bin/activate
python main.py
```

`Ctrl+C` で終了します。

### 設定のカスタマイズ

メニューバーから **設定ファイルを開く** を選択すると `~/.kikitori_settings.yaml` が作成・表示されます。

```yaml
language: ja
prompt: "以下は日本語の音声認識結果です。"
hotkey:
  - option
min_duration_ms: 500
```

- `language`: 認識言語（`ja`, `en`, `zh` など）
- `prompt`: Whisper への指示文（文脈を与えると認識精度が向上）
- `hotkey`: ホットキー（後述）
- `min_duration_ms`: 最低録音長（ミリ秒）。これより短い録音はWhisperに渡さない（デフォルト: 500）

ファイル保存後、自動的に設定が反映されます。

**利用可能なホットキー例:**
- `["option"]` — Option 単体
- `["ctrl", "alt"]` — Ctrl + Option
- `["f13"]` — F13 キー
- `["cmd", "shift", "a"]` — Cmd + Shift + A

### メニューバー操作

画面右上の 🎤 アイコンをクリック:

| メニュー | 動作 |
|---------|------|
| ○ 待機中 / ● 録音中... | 現在の状態を表示 |
| 🔴 録音開始 / ⏹ 録音停止 | ホットキーなしで録音操作 |
| 言語: ja | 現在の認識言語 |
| プロンプト: ... | 現在のプロンプト（30文字まで表示） |
| モデル: ... | 使用中のWhisperモデル |
| 設定ファイルを開く | `~/.kikitori_settings.yaml` を編集 |
| 終了 | アプリを終了 |

> 初回起動時、`mlx-whisper` が Hugging Face からモデルをダウンロードします（数百MB）。ネットワーク接続が必要です。

## 開発

### テストの実行

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

### プロジェクト構成

```
.
├── main.py                  # CLI エントリポイント
├── menu_bar_app.py          # macOS メニューバーアプリ（rumps版）
├── pyside_main.py           # PySide6 版エントリポイント（オーバーレイUI付き）
├── run.sh                   # 起動スクリプト
├── requirements.txt         # Python 依存関係
└── kikitori/
    ├── app.py               # アプリケーション統合
    ├── audio_buffer.py      # スレッドセーフ録音バッファ
    ├── config.py            # 設定定数
    ├── hotkey_manager.py    # ホットキー状態管理
    ├── injector.py          # クリップボード経由テキスト入力
    ├── overlay.py           # PySide6 オーバーレイUI
    ├── recorder.py          # 録音ストリーム制御
    ├── transcriber.py       # mlx-whisper ラッパー
    └── ui_pyside.py         # PySide6 メニューバー＋オーバーレイ統合

Homebrew Formula: [`konyu/homebrew-kikitori`](https://github.com/konyu/homebrew-kikitori)
```

## トラブルシューティング

### ホットキーが効かない

1. システム設定 → プライバシーとセキュリティ → アクセシビリティ で **ターミナル.app**（または iTerm.app）に ✅ が付いているか確認
2. Karabiner-Elements、BetterTouchTool など他のキー監視アプリを一時的に無効化
3. メニューバーから「🔴 録音開始」をクリックして動作確認（メニュー操作で録音できれば権限問題）

### マイク入力が取得できない

システム設定 → プライバシーとセキュリティ → マイク でターミナル.app に ✅

### 音声認識結果が入力されない

1. 対象アプリ（メモ帳、VS Code など）にカーソルが置かれているか確認
2. 対象アプリにもアクセシビリティ権限が必要な場合があります

### モデルのダウンロードに失敗する

```bash
rm -rf ~/.cache/huggingface
./run.sh  # 再試行
```

## 技術的補足

### 配布方法について

本アプリは **Homebrew Formula** で配布しています。以下の理由により `.app` バンドル（PyInstaller/py2app）は提供していません：

- **mlx-whisper** が Metal GPU ライブラリ（`.metallib`）と C++ 拡張を含み、正しく梱包するのが極めて困難
- **sounddevice** が PortAudio（`.dylib`）に依存し、署名・リンクの問題が発生
- **PySide6** が Qt フレームワークを必要とし、サイズが膨大になる（2GB以上）

Homebrew 経由ならこれらの依存関係を自動的に解決でき、また `kikitori` コマンドで簡単に起動できます。

### 使用ライブラリ

| ライブラリ | 用途 |
|-----------|------|
| [mlx-whisper](https://github.com/ml-explore/mlx-whisper) | Apple Silicon 最適化音声認識 |
| [sounddevice](https://python-sounddevice.readthedocs.io/) | マイク録音 |
| [pynput](https://pynput.readthedocs.io/) | グローバルホットキー監視 |
| [pyperclip](https://pyperclip.readthedocs.io/) | クリップボード操作 |
| [rumps](https://rumps.readthedocs.io/) | macOS メニューバー UI |
| [PySide6](https://doc.qt.io/qtforpython-6/) | PySide6 版 GUI（オーバーレイ・メニューバー） |

## ライセンス

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
