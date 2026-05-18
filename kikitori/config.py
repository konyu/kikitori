"""アプリケーション設定定数"""
from pathlib import Path

import numpy as np

# 音声設定
SAMPLE_RATE: int = 16000
CHANNELS: int = 1
AUDIO_DTYPE = np.float32

# Whisperモデル設定
MODEL_NAME: str = "mlx-community/whisper-large-v3-turbo"
DEFAULT_LANGUAGE: str = "ja"
DEFAULT_PROMPT: str = "以下は日本語の音声認識結果です。"

# 録音設定
MAX_DURATION: float = 60.0  # 秒
MIN_DURATION_MS: float = 500.0  # ミリ秒（これより短い録音は誤動作としてWhisperに渡さない）
SILENCE_RMS_THRESHOLD: float = 0.01  # RMS閾値（これ以下は無音とみなしてWhisperに渡さない）

# ホットキー設定（設定ファイルで変更可能）
# 例: ["f13"], ["ctrl", "alt"], ["cmd"], ["shift", "f13"]
DEFAULT_HOTKEY: list[str] = ["option"]

# 専門用語集ファイルパス
GLOSSARY_PATH: Path = Path.home() / ".kikitori_glossary.yaml"
