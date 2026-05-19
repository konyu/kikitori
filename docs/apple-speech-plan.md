# Apple Speech Framework 実装計画

> Kikitori に Apple の `SFSpeechRecognizer` を統合し、mlx-whisper と並行して使えるようにする。
> ブランチ: `feature/apple-speech-framework`
> 作成日: 2026-05-19

---

## Goal

- `SpeechTranscriber`：バッチ音声認識（録音後に一括変換）。既存 `Transcriber` と同じ `transcribe(audio, prompt, language) -> str` インターフェース。
- `SpeechAnalyzer`：リアルタイム音声分析（録音中に逐次認識結果をコールバックで通知）。
- 既存の `mlx-whisper` 実装と**並行して使える DI 設計**を維持。

---

## Evidence

| 項目 | 確認内容 |
|------|----------|
| 既存 Transcriber インターフェース | `transcribe(audio: np.ndarray, prompt="", language="ja") -> str` |
| HotkeyManager の結合 | `_transcriber.transcribe(...)` をダックタイピングで呼び出す |
| AudioBuffer 出力形式 | `float32`, 16000Hz, モノラルの `np.ndarray` |
| PyObjC Speech 利用可否 | `pyobjc-framework-Speech` で `SFSpeechRecognizer` / `SFSpeechAudioBufferRecognitionRequest` が使える |
| 追加依存 | `pyobjc-framework-Speech` |
| 既知の問題 | IDE 実行で `SIGABRT`（exit code 134）の可能性 → **ターミナル実行推奨**。`bestTranscription` が `None` になるケースあり → **null チェック必須** |
| オフライン認識 | macOS 14+ で `requiresOnDeviceRecognition = True` を設定可能 |
| AVAudioPCMBuffer | PyObjC v3.12 で `floatChannelData` の binding 修正あり。NumPy → `AVAudioPCMBuffer` には `ctypes` によるポインタコピーが必要な可能性 |

---

## Uncertainties

1. **NumPy → AVAudioPCMBuffer の変換** → 難航した場合、`SpeechAnalyzer` は一時 WAV ファイルを逐次更新し `SFSpeechURLRecognitionRequest` でポーリングするフォールバックに切り替える。
2. **Speech Recognition の macOS 権限** → 初回実行時に `NSSpeechRecognitionUsageDescription` が要求される可能性。現状の Homebrew/CLI 配布では `Info.plist` がないため、ユーザーに手動で「システム設定 → プライバシーとセキュリティ → 音声認識」の許可が必要になる可能性。
3. **日本語認識精度** → Apple Speech は日本語対応だが、mlx-whisper と比較して専門用語の精度が低い可能性。設定ファイルで切り替え可能にする。
4. **`prompt` パラメータ** → Apple Speech は Whisper の `initial_prompt` に相当する機能がない。`prompt` は無視、または glossary 文字列を事前テキストとして結合する workaround にする。

---

## Plan

### Step 1: 新規ファイル作成

#### `kikitori/apple_speech.py`

| クラス | 責務 | 主要メソッド |
|--------|------|-------------|
| `SpeechTranscriber` | バッチ音声認識（Transcriber 互換） | `__init__(locale="ja-JP", on_device=True)`, `load()`, `transcribe(audio, prompt, language) -> str` |
| `SpeechAnalyzer` | リアルタイム音声分析 | `__init__(locale="ja-JP", on_device=True)`, `start()`, `stop()`, `append_audio(audio: np.ndarray)`, `on_partial_result`, `on_final_result` コールバック |

実装方針：
- `SpeechTranscriber`：一時 WAV ファイルに書き出し → `SFSpeechURLRecognitionRequest` → `SFSpeechRecognizer.recognitionTaskWithRequest_resultHandler_` → 結果を `str` で返却。
- `SpeechAnalyzer`：`SFSpeechAudioBufferRecognitionRequest` を生成 → `AVAudioFormat(16000, 1)` + `AVAudioPCMBuffer` を作成 → `ctypes` 経由で `floatChannelData` に NumPy 配列をコピー → `appendAudioPCMBuffer_` で逐次投入。

#### `tests/test_apple_speech.py`
- `SpeechTranscriber`：モック `SFSpeechRecognizer` で `bestTranscription.formattedString` を返すテスト。
- `SpeechAnalyzer`：モック `SFSpeechAudioBufferRecognitionRequest` で `appendAudioPCMBuffer_` が呼ばれること、`stop()` でタスクがキャンセルされることを検証。

### Step 2: 既存ファイル変更

| ファイル | 変更内容 |
|----------|----------|
| `requirements.txt` | `pyobjc-framework-Speech` を追加 |
| `kikitori/config.py` | `APPLE_SPEECH_LOCALE`, `APPLE_SPEECH_ON_DEVICE` などの定数を追加 |
| `kikitori/app.py` | `App.__init__` に `transcriber` パラメータを追加。デフォルトは既存 `Transcriber` のまま。 |

### Step 3: テスト・動作確認

```bash
source venv/bin/activate
pip install pyobjc-framework-Speech
python -m pytest tests/test_apple_speech.py -v

# 手動バッチ認識テスト
python -c "from kikitori.apple_speech import SpeechTranscriber; t=SpeechTranscriber(); t.load(); print('ok')"
```

### Step 4: ドキュメント更新

- `README.md` に Apple Speech 使用時の注意（権限・ターミナル実行推奨）を追記。
- `AGENTS.md` の依存ライブラリ表に `pyobjc-framework-Speech` を追加。

---

## Risks

| リスク | 対策 |
|--------|------|
| `AVAudioPCMBuffer` への NumPy コピーが不可 | `SpeechAnalyzer` を一時 WAV ファイル方式にフォールバック |
| `SIGABRT` / `bestTranscription` None クラッシュ | resultHandler 内で徹底的な null チェック。IDE 経由ではなくターミナル直接実行で検証 |
| Speech 権限ダイアログが出ない | `tccutil reset SpeechRecognition` でリセットして再テスト |
| 日本語認識品質が低い | 設定ファイルで `model_type: "mlx_whisper"` / `"apple_speech"` を切り替え可能にする。デフォルトは `mlx_whisper` |
| ブランチ破棄 | 既存 `Transcriber` / `app.py` のデフォルト動作を一切変更しないため、ブランチ削除で元の状態に完全復元可能 |

---

## 別セッション実行用チェックリスト

```
□ git checkout -b feature/apple-speech-framework
□ requirements.txt に pyobjc-framework-Speech を追加
□ kikitori/apple_speech.py を新規作成（SpeechTranscriber + SpeechAnalyzer）
□ tests/test_apple_speech.py を新規作成
□ kikitori/config.py に APPLE_SPEECH_* 定数を追加
□ kikitori/app.py に transcriber 注入パラメータを追加
□ pytest tests/test_apple_speech.py -v
□ python main.py で手動テスト（ターミナル直接実行）
□ docs/apple-speech-plan.md を作成
□ README.md / AGENTS.md を更新
□ git add . && git commit -m "feat: add Apple Speech framework support"
```
