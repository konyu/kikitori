"""音声認識（mlx-whisper ラッパー）"""
from typing import Callable

import numpy as np

import mlx_whisper


class Transcriber:
    def __init__(
        self,
        model_name: str,
        transcribe_func: Callable = None,
        load_model_func: Callable = None,
    ):
        self._model_name = model_name
        self._transcribe = transcribe_func or mlx_whisper.transcribe
        self._load_model = load_model_func or mlx_whisper.load_models.load_model
        self._model = None

    def load(self):
        self._model = self._load_model(self._model_name)

    def transcribe(
        self,
        audio: np.ndarray,
        prompt: str = "",
        language: str = "ja",
    ) -> str:
        if audio.size == 0:
            return ""
        result = self._transcribe(
            audio,
            path_or_hf_repo=self._model_name,
            initial_prompt=prompt,
            language=language,
            verbose=False,
        )
        return result.get("text", "").strip()
