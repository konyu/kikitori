# VoiceToText — 配布・セットアップ手順

## 概要

Apple Silicon Mac 向け音声認識ツール。ホットキー（Ctrl + Option）押下中にマイク入力を録音し、解放時に音声認識結果をクリップボード経由で自動入力します。

**実行方式**: ターミナルから仮想環境経由で起動（メニューバー常駐型）

> ⚠️ **バイナリ（.app）化について**: PyInstaller や py2app で生成した `.app` は macOS のアクセシビリティ権限管理（TCC）と正しく連携しないことが確認されています。ホットキー機能が必須のため、**ターミナル実行を推奨**します。

---

## 動作環境

- macOS（Apple Silicon / Intel）
- Python 3.10 〜 3.14
- マイク入力デバイス
- **ターミナル.app（または iTerm.app）にアクセシビリティ権限が必要**

---

## セットアップ手順

### 1. リポジトリをクローンまたは展開

```bash
cd /path/to/whisper
```

### 2. Python 仮想環境を作成

```bash
python3 -m venv venv
```

### 3. 依存パッケージをインストール

```bash
source venv/bin/activate
pip install -r requirements.txt
```

> 初回実行時、`mlx_whisper` が Hugging Face から AI モデルをダウンロードします（数百MB）。ネットワーク接続が必要です。

### 4. アクセシビリティ権限を付与

**ホットキー（Ctrl + Option）を使うには、ターミナルにアクセシビリティ権限が必要です。**

1. **システム設定** → **プライバシーとセキュリティ** → **アクセシビリティ**
2. 左下の🔓をクリックしてロック解除
3. **ターミナル.app**（または iTerm.app）をリストに追加し、✅ にチェック

![アクセシビリティ設定](https://support.apple.com/library/content/dam/edam/applecare/images/ja_JP/macos/monterey/macos-monterey-system-prefs-security-privacy-accessibility.png)

> 既にターミナルに権限が付いていれば、この手順は不要です。

---

## 起動方法

### 方法 A: ランチャースクリプトを使う（推奨）

```bash
./run.sh
```

### 方法 B: 直接 Python を実行

```bash
source venv/bin/activate
python menu_bar_app.py
```

---

## 使い方

### 録音・音声認識

| 操作 | 動作 |
|------|------|
| **Ctrl + Option を押す** | 録音開始（メニューバーアイコンが 🔴 に変わる） |
| **Ctrl + Option を離す** | 録音停止 → 音声認識 → カーソル位置に自動入力 |

### メニューバーからの操作

画面右上の 🎤 アイコンをクリック:

- **🔴 録音開始** — ホットキーなしで録音開始
- **⏹ 録音停止** — 録音停止して認識結果を入力
- **言語: ja** — 現在の認識言語を表示
- **プロンプト: ...** — 現在のプロンプトを表示
- **設定ファイルを開く** — `~/.voice_to_text_settings.json` を編集
- **終了** — アプリを終了

### 設定ファイル

`~/.voice_to_text_settings.json` を編集して言語・プロンプトを変更:

```json
{
  "language": "ja",
  "prompt": "以下は日本語の会話です。"
}
```

- `language`: 認識言語（`ja`, `en`, `zh` など）
- `prompt`: Whisper モデルへの指示文（文脈を与えると認識精度が向上）

ファイル保存後、自動的に設定が反映されます。

---

## ファイル構成

```
.
├── menu_bar_app.py           # メニューバーUIエントリポイント
├── main.py                   # コマンドライン版エントリポイント
├── run.sh                    # 起動ランチャースクリプト
├── requirements.txt          # Python 依存パッケージ
├── DISTRIBUTION.md           # このファイル
├── voice_to_text/            # メインアプリケーションロジック
│   ├── __init__.py
│   ├── app.py                # アプリケーション統合
│   ├── audio_buffer.py       # 音声データバッファ
│   ├── config.py             # 設定定数
│   ├── hotkey_manager.py     # ホットキー状態管理
│   ├── injector.py           # キー入力自動化
│   ├── recorder.py           # マイク録音
│   └── transcriber.py        # 音声認識（mlx-whisper ラッパー）
└── tests/                    # テストスイート
```

---

## トラブルシューティング

### ホットキーが効かない

1. **ターミナルにアクセシビリティ権限が付いているか確認**
   - システム設定 → プライバシーとセキュリティ → アクセシビリティ
   - ターミナル.app に ✅ が付いていることを確認

2. **他のキー監視アプリと競合していないか確認**
   - Karabiner-Elements、BetterTouchTool などを一時的に無効化

3. **メニューバーから「🔴 録音開始」をクリックして動作確認**
   - メニュークリックで録音できれば、権限問題の可能性が高い

### モデルのダウンロードに失敗する

```bash
# Hugging Face キャッシュをクリアして再試行
rm -rf ~/.cache/huggingface
# 再度アプリを起動
./run.sh
```

### マイク入力が取得できない

1. システム設定 → プライバシーとセキュリティ → マイク
2. ターミナル.app に ✅ が付いていることを確認

### 音声認識結果が入力されない

1. 対象アプリ（メモ帳、VS Code など）にカーソルが置かれているか確認
2. 対象アプリもアクセシビリティ権限が必要な場合がある

---

## 技術的補足

### なぜ .app 化できないのか

macOS の TCC（Transparency, Consent, and Control）システムは、アクセシビリティ権限を**実行ファイルのコード署名ハッシュ（CDHash）**に紐付けます。PyInstaller や py2app で生成した `.app` は ad-hoc 署名のため、TCC が正しく認識せず、毎回権限を求められても無限ループになる問題が確認されました。

Developer ID 証明書（Apple Developer Program、年額 $99）で署名すれば解決しますが、個人利用・開発用途ではターミナル実行が最も確実です。

### 使用ライブラリ

| ライブラリ | 用途 |
|-----------|------|
| [mlx-whisper](https://github.com/ml-explore/mlx-whisper) | Apple Silicon 最適化音声認識 |
| [sounddevice](https://python-sounddevice.readthedocs.io/) | マイク録音（PortAudio 経由） |
| [pynput](https://pynput.readthedocs.io/) | キーボードホットキー監視 |
| [pyperclip](https://pyperclip.readthedocs.io/) | クリップボード操作 |
| [rumps](https://rumps.readthedocs.io/) | macOS メニューバー UI |
