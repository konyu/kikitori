# Voice to Text Injection Tool - Requirements & TODO

## Requirements (システム要件)

### 動作環境
- Apple Silicon Mac (M1/M2/M3)
- Python 3.10以上

### 依存モジュール
- `mlx-whisper`: 音声認識（Apple Silicon最適化）
- `sounddevice`: マイク入力の取得
- `numpy`: 音声データのオンメモリ配列処理
- `pynput`: グローバルホットキー監視
- `pyperclip`: クリップボード経由のテキスト入力（日本語入力の安定化）
- `ffmpeg`: 音声処理基盤（Homebrew経由でインストール）

### OS権限
- マイク（システム設定 > プライバシーとセキュリティ）
- アクセシビリティ（システム設定 > プライバシーとセキュリティ）

---

## TODO (実装タスクリスト)

### 1. 環境構築
- [x] `brew install ffmpeg` 実行
- [x] Python仮想環境（venv）作成・有効化
- [x] `pip install mlx-whisper sounddevice numpy pynput pyperclip` 実行

### 2. コンポーネント実装
- [x] **録音モジュール**: `sounddevice`で16000Hz・モノラルのマイク入力を取得し、`numpy`配列としてオンメモリで保持・結合する処理作成。
- [x] **推論モジュール**: 取得した`numpy`配列を`mlx-whisper.transcribe`に渡し、テキストを抽出する処理作成。モデルは`mlx-community/whisper-large-v3-turbo`等を指定。日本語用プロンプト注入も実装。
- [x] **出力モジュール**: 抽出テキストを`pyperclip`でクリップボードにコピーし、`pynput`でペースト（`Cmd + V`）をエミュレートする処理作成。
- [x] **制御モジュール**: `pynput`のリスナーを用いて特定のホットキー（例：`Ctrl + Option`）の押下・解放を検知する処理作成。押下中で録音開始、解放で録音停止・推論・出力を実行。

### 3. スクリプト統合
- [x] 上記コンポーネントを結合した1つのPythonスクリプト作成。
- [x] 起動時のモデル読み込み完了ログ追加。

### 4. 動作確認
- [x] スクリプト実行（初回はモデルダウンロード発生）。
- [ ] macOSのシステム設定から、実行しているターミナル/エディタにマイクとアクセシビリティの権限付与。
- [ ] ブラウザやエディタの入力欄にフォーカス。
- [ ] ホットキー押下で発声、解放でテキストが自動入力・ペーストされることの確認。
