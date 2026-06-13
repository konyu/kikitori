# AGENTS.md — Kikitori

macOS 向け音声認識入力ツール。ホットキー押下中に録音し、解放時に Apple Speech Framework でテキスト変換・自動ペーストする macOS メニューバーアプリ（オーバーレイUI付き）。

## プロジェクト構成

```
.
├── pyside_main.py           # アプリ起動エントリポイント
├── requirements.txt         # Python 依存関係
├── assets/                  # アイコン画像
├── tests/                   # pytest テスト
└── kikitori/                # メインパッケージ
    ├── __init__.py
    ├── app.py               # アプリ統合（App クラス）
    ├── apple_speech.py      # Apple Speech Framework ラッパー（SFSpeechRecognizer）
    ├── audio_buffer.py      # スレッドセーフ録音バッファ（numpy 配列）
    ├── config.py            # 設定定数（VERSION, DEFAULT_HOTKEY 等）
    ├── hotkey_manager.py    # ホットキー状態管理（pynput リスナー制御・録音→推論パイプライン）
    ├── injector.py          # クリップボード経由テキスト入力（pyperclip + pynput Cmd+V）
    ├── overlay.py           # PySide6 オーバーレイUI（波形アニメーション）
    ├── recorder.py          # 録音ストリーム制御（sounddevice InputStream）
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
pytest tests/ -v

# アプリ起動（オーバーレイUI付き）
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
- GitHub Actions を用いて `vX.Y.Z` タグプッシュ時に bottle ビルドと Homebrew リポジトリの更新を全自動化。

## 主要な技術的制約

- **macOS要要件**: macOS 14.0 (Sonoma) 以上必須。
- **推奨環境**: Apple Silicon Mac 推奨（`SFSpeechRecognizer` のオンデバイス完全ローカル音声認識を安定利用するため）。
- **動作に必要な権限**:
  - マイク（システム設定 → プライバシーとセキュリティ → マイク）
  - アクセシビリティ（システム設定 → プライバシーとセキュリティ → アクセシビリティ）
  - 音声認識（初回起動時に許可ダイアログが表示される）
- **配布・インストール**: Homebrew Formula (bottle) 経由。
- **設定ファイル**: `~/.kikitori_settings.yaml` （language, prompt, hotkey, min_duration_ms）
- **デフォルトホットキー**: 右 Option キー
- **録音**: 16000Hz, モノラル, float32, 最低500ms（誤動作防止）
- **Apple Speech Framework (`apple_speech.py`)**: 
  - `requiresOnDeviceRecognition = True` を指定し、ローカル完結での認識を強制（macOS 14以降での動作を前提）。

## 依存ライブラリ

| ライブラリ | 用途 |
|-----------|------|
| `PySide6-Essentials` | オーバーレイ UI 版 GUI、メニューバー（QtWebEngine 等を含まない軽量版） |
| `sounddevice` | マイク録音（PortAudio） |
| `numpy` | 音声データ配列処理 |
| `pynput` | グローバルホットキー監視・キーエミュレーション |
| `pyperclip` | クリップボード操作 |
| `pyobjc-framework-Speech` | Apple Speech Framework 連携（`SFSpeechRecognizer`） |
| `pyobjc-framework-Cocoa` | macOS Cocoa フレームワーク連携 |
| `pyobjc-framework-AVFoundation` | 音声認識フレームワークの内部依存解決用 |
| `pyyaml` | 設定ファイル読み込み |
| `pytest` | テストフレームワーク |
