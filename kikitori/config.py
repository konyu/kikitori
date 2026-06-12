"""アプリケーション設定定数"""
import os
from pathlib import Path

import numpy as np

# 音声設定
SAMPLE_RATE: int = 16000
CHANNELS: int = 1
AUDIO_DTYPE = np.float32

# Whisperモデル設定
MODEL_NAME: str = "mlx-community/whisper-large-v3-turbo"
DEFAULT_LANGUAGE: str = "ja"

# 録音設定
MAX_DURATION: float = 60.0  # 秒
MIN_DURATION_MS: float = 300.0  # ミリ秒（これより短い録音は誤動作として無視）
SILENCE_RMS_THRESHOLD: float = 0.0001  # RMS閾値（これ以下は無音とみなす）

# ホットキー設定（設定ファイルで変更可能）
# 例: ["f13"], ["ctrl", "alt"], ["cmd"], ["shift", "f13"]
DEFAULT_HOTKEY: list[str] = ["option"]

# Apple Speech Framework 設定
APPLE_SPEECH_LOCALE: str = "ja-JP"
APPLE_SPEECH_ON_DEVICE: bool = False  # オンデバイス日本語モデル未インストールの場合サーバー認識にフォールバック
DEFAULT_TRANSCRIBER_TYPE: str = "apple_speech"  # "mlx_whisper" or "apple_speech"

# 計測モード（環境変数 BENCHMARK_MODE=true または True 定数で各段階のレイテンシログを出力）
BENCHMARK_MODE: bool = os.environ.get("BENCHMARK_MODE", "").lower() in ("true", "1", "yes")

# デバッグログモード（環境変数 DEBUG=true で詳細なデバッグログを出力）
DEBUG: bool = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")

# 専門用語集ファイルパス
GLOSSARY_PATH: Path = Path.home() / ".kikitori" / "glossary.yaml"
