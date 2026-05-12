"""アプリケーション設定定数"""

# 音声設定
SAMPLE_RATE: int = 16000
CHANNELS: int = 1
AUDIO_DTYPE: str = "float32"

# Whisperモデル設定
MODEL_NAME: str = "mlx-community/whisper-large-v3-turbo"
DEFAULT_LANGUAGE: str = "ja"
DEFAULT_PROMPT: str = "以下は日本語の音声認識結果です。"

# 録音設定
MAX_DURATION: float = 60.0  # 秒

# ホットキー設定（設定ファイルで変更可能）
# 例: ["f13"], ["ctrl", "alt"], ["cmd"], ["shift", "f13"]
DEFAULT_HOTKEY: list[str] = ["option"]

# クリップボード設定
CLIPBOARD_POLL_INTERVAL: float = 0.01  # 秒
CLIPBOARD_MAX_WAIT: float = 1.0  # 秒
