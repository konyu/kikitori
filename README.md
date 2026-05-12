# 🎤 VoiceToText

macOS 向け音声認識入力ツール。ホットキー押下中にマイク入力を録音し、解放時に Apple Silicon 最適化された Whisper モデルが音声をテキストに変換、クリップボード経由で自動ペーストします。

## 特徴

- **Apple Silicon 最適化**: `mlx-whisper` による高速な音声認識（M1/M2/M3/M4/M5）
- **ホットキー操作**: 設定可能なホットキー（デフォルト: Option） — 押下中録音、解放で即時テキスト化
- **メニューバー常駐**: `rumps` による macOS メニューバーアプリ（ターミナル実行推奨）
- **設定ファイル対応**: ホットキー・言語・プロンプトを JSON ファイルでカスタマイズ可能
- **最大60秒録音**: 長時間録音の自動区切り機能

## 動作環境

- Apple Silicon Mac（M1/M2/M3/M4/M5）
- Python 3.10 以上
- macOS 14（Sonoma）以上推奨

## 必要な権限

| 権限 | 設定場所 | 用途 |
|------|---------|------|
| マイク | システム設定 → プライバシーとセキュリティ → マイク | 音声入力 |
| アクセシビリティ | システム設定 → プライバシーとセキュリティ → アクセシビリティ | グローバルホットキー監視・自動ペースト |

## インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd whisper

# 仮想環境の作成と有効化
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

### コマンドラインから直接実行

```bash
source venv/bin/activate
python main.py
```

`Ctrl+C` で終了します。

### 設定のカスタマイズ

メニューバーから **設定ファイルを開く** を選択すると `~/.voice_to_text_settings.json` が作成・表示されます。

```json
{
  "language": "ja",
  "prompt": "以下は日本語の音声認識結果です。",
  "hotkey": ["option"]
}
```

**利用可能なホットキー例:**
- `["option"]` — Option 単体
- `["ctrl", "alt"]` — Ctrl + Option
- `["f13"]` — F13 キー
- `["cmd", "shift", "a"]` — Cmd + Shift + A

設定ファイルを保存すると、アプリが自動的に再読み込みします。

## ログイン時自動起動（毎回の手動実行が不要に）

```bash
./setup_autostart.sh
```

これで以下が自動設定されます：
- **Launch Agent**: Mac 起動時に自動でバックグラウンド実行
- **ログローテーション**: `newsyslog` によりログファイルが 1MB 単位で自動ローテーション（最大3世代、bzip2 圧縮）

> ⚠️ **重要**: Launch Agent 経由で起動する場合、ターミナルとは別プロセスになるため、
> **Python バイナリ自体** にアクセシビリティ権限を付与する必要があります。
> `setup_autostart.sh` 実行時に案内が表示されます。
>
> 手動設定: システム設定 → プライバシーとセキュリティ → アクセシビリティ →
> `venv/bin/python` を追加して ✅

```bash
# 起動確認
launchctl list | grep voicetotext

# ログ確認
tail -f /tmp/voicetotext.log

# 停止したい場合
launchctl unload ~/Library/LaunchAgents/com.voicetotext.plist
```

### 手動セットアップの場合

**Launch Agent plist**（`~/Library/LaunchAgents/com.voicetotext.plist`）:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.voicetotext</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/whisper/run.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/whisper</string>
    <key>StandardOutPath</key>
    <string>/tmp/voicetotext.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/voicetotext.err</string>
</dict>
</plist>
```

**ログローテーション**（`/etc/newsyslog.d/voicetotext.conf`）:

```
/tmp/voicetotext.log       <uid>  staff  644  3  1024  *  JN
/tmp/voicetotext.err       <uid>  staff  644  3  1024  *  JN
```

```bash
launchctl load ~/Library/LaunchAgents/com.voicetotext.plist
```

## 開発

### テストの実行

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

### プロジェクト構成

```
.
├── main.py                       # CLI エントリポイント
├── menu_bar_app.py               # macOS メニューバーアプリ
├── run.sh                        # 起動スクリプト
├── setup_autostart.sh            # 自動起動＆ログローテーション セットアップ
├── com.voicetotext.plist         # Launch Agent 設定
├── voicetotext.newsyslog.conf    # ログローテーション設定
├── requirements.txt              # Python 依存関係
├── tests/
│   ├── conftest.py               # pynput macOS スレッドハング対策
│   └── ...
└── voice_to_text/
    ├── app.py                    # アプリケーション統合
    ├── audio_buffer.py           # スレッドセーフ録音バッファ
    ├── config.py                 # 設定定数
    ├── hotkey_manager.py         # ホットキー状態管理
    ├── injector.py               # クリップボード経由テキスト入力
    ├── recorder.py               # 録音ストリーム制御
    └── transcriber.py            # mlx-whisper ラッパー
```

## トラブルシューティング

### ホットキーが効かない

1. **アクセシビリティ権限を確認**: システム設定 → プライバシーとセキュリティ → アクセシビリティ
   - ターミナル.app（または iTerm.app）に ✅
   - Launch Agent 使用時は `venv/bin/python` にも ✅
2. **マイク権限を確認**: 同様にマイクの設定も確認
3. 設定後はアプリを再起動してください

### Launch Agent が起動しない

```bash
# ステータス確認
launchctl list | grep voicetotext
# 終了コードが 0 以外ならエラー

# ログ確認
tail -20 /tmp/voicetotext.err

# 再読み込み
launchctl unload ~/Library/LaunchAgents/com.voicetotext.plist
launchctl load ~/Library/LaunchAgents/com.voicetotext.plist
```

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
