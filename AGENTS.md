# AGENTS.md — Kikitori

Apple Silicon Mac 向け音声認識入力ツール。ホットキー押下中に録音し、解放時に `mlx-whisper` でテキスト変換・自動ペーストする macOS メニューバーアプリ。

## プロジェクト構成

```
.
├── main.py                  # CLI エントリポイント（kikitori.app.App を起動）
├── menu_bar_app.py          # rumps 版メニューバーアプリ
├── pyside_main.py           # PySide6 版（オーバーレイUI付き）
├── run.sh                   # 起動スクリプト（仮想環境チェック・権限チェック）
├── setup.py                 # py2app ビルド設定（非推奨、Homebrew Formula で配布）
├── requirements.txt         # Python 依存関係
├── assets/                  # アイコン画像（icon-idle.png, icon-recording.png）
├── tests/                   # pytest テスト
└── kikitori/                # メインパッケージ
    ├── __init__.py
    ├── app.py               # アプリ統合（App クラス）
    ├── apple_speech.py      # Apple Speech Framework ラッパー（SFSpeechRecognizer）
    ├── audio_buffer.py      # スレッドセーフ録音バッファ（numpy 配列）
    ├── config.py            # 設定定数（SAMPLE_RATE, MODEL_NAME, DEFAULT_HOTKEY 等）
    ├── hotkey_manager.py    # ホットキー状態管理（pynput リスナー制御・録音→推論パイプライン）
    ├── injector.py          # クリップボード経由テキスト入力（pyperclip + pynput Cmd+V）
    ├── overlay.py           # PySide6 オーバーレイUI（波形アニメーション）
    ├── recorder.py          # 録音ストリーム制御（sounddevice InputStream）
    ├── transcriber.py       # mlx-whisper ラッパー（依存注入対応）
    └── ui_pyside.py         # PySide6 メニューバー＋オーバーレイ統合
```

## 開発コマンド

すべてプロジェクトルートから実行。

```bash
# 仮想環境（Python 3.14 via mise）
mise exec python -- python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# テスト実行
python -m pytest tests/ -v

# CLI モードで起動
python main.py

# メニューバーアプリ起動
./run.sh

# PySide6 版起動（オーバーレイUI付き）
python pyside_main.py
```

## コーディング規約

### 全般
- Python 3.14（mise でバージョン管理: `mise.toml`）
- 日本語コメント・ドキュメントは日本語（docstring は日本語）
- 型アノテーションを積極的に使用（`list[str]`, `np.ndarray` 等）
- 依存注入可能な設計（`transcribe_func`, `listener_factory` 等をコンストラクタで受け取る）
- テスト容易性を重視（Fake ストリーム、依存注入）

### スタイル
- ダブルクォート文字列（docstring）
- 4スペースインデント
- プライベートメンバーは `_` プレフィックス
- 定数は `UPPER_SNAKE_CASE`（`config.py`）
- import は標準ライブラリ → サードパーティ → プロジェクト内部 の順

### アーキテクチャパターン
- `App` クラスが各コンポーネントを DI で組み立て（`app.py`）
- `AudioBuffer` はスレッドセーフ（`threading.Lock` 使用）
- `Transcriber` / `Recorder` はテスト用に関数注入可能
- 設定値は `kikitori.config` に集約
- Homebrew Formula は別リポジトリ `konyu/homebrew-kikitori` で管理（`Formula/` はアプリ本体に含めない）

## 主要な技術的制約

- **Apple Silicon 専用**: M1/M2/M3/M4。Intel Mac 非対応（`mlx-whisper` が Metal GPU 必須）
- **macOS 14+ 推奨**: アクセシビリティ API・マイク権限
- **動作に必要な権限**:
  - マイク（システム設定 → プライバシーとセキュリティ → マイク）
  - アクセシビリティ（システム設定 → プライバシーとセキュリティ → アクセシビリティ）
- **配布は Homebrew Formula**: py2app/PyInstaller は mlx-whisper の `.metallib` や PortAudio `.dylib` のバンドルが困難なため非推奨
- **初回起動時**: `mlx-whisper` が Hugging Face からモデル（数百MB）をダウンロード
- **設定ファイル**: `~/.kikitori_settings.yaml` （language, prompt, hotkey, min_duration_ms）
- **デフォルトホットキー**: Option 単体
- **録音**: 16000Hz, モノラル, float32, 最大60秒, 最低500ms（誤動作防止）
- **Apple Speech Framework**: IDE 実行で `SIGABRT` の可能性があるためターミナル直接実行推奨。`prompt` 引数は無視される。オフライン認識は macOS 14+ で `requiresOnDeviceRecognition = True`

## 依存ライブラリ

| ライブラリ | 用途 |
|-----------|------|
| `mlx-whisper` | Apple Silicon 最適化 Whisper 音声認識 |
| `sounddevice` | マイク録音（PortAudio） |
| `numpy` | 音声データ配列処理 |
| `pynput` | グローバルホットキー監視・キーエミュレーション |
| `pyperclip` | クリップボード操作 |
| `rumps` | macOS メニューバー UI（軽量） |
| `PySide6` | オーバーレイ UI 版 GUI |
| `pyobjc-framework-Cocoa` | macOS Cocoa フレームワーク連携 |
| `pyyaml` | 設定ファイル読み込み |
| `pytest` | テストフレームワーク |
| `pyobjc-framework-Speech` | Apple Speech Framework 連携（`SFSpeechRecognizer`） |
