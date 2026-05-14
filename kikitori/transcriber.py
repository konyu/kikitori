"""音声認識（mlx-whisper ラッパー）"""
from typing import Callable

import numpy as np

import mlx_whisper

from kikitori.config import DEFAULT_LANGUAGE


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
        self._call_count = 0  # デバッグ用: transcribe呼び出し回数

    def load(self):
        """モデルファイルのキャッシュ確認のみ行う。

        実際の MLX モデルロードは、初回 transcribe() 呼び出し時に
        ModelHolder が pynput スレッド内で行う（GPU Stream の制約のため）。
        ここでは HuggingFace キャッシュの確認のみで、メモリ消費しない。
        """
        import sys
        from pathlib import Path

        model_path = Path(self._model_name)
        try:
            from huggingface_hub import try_to_load_from_cache
            cached = try_to_load_from_cache(repo_id=self._model_name, filename="config.json")
        except Exception:
            cached = None

        if model_path.exists():
            print(f"[INFO] モデルパス確認: {self._model_name} (ローカル)", flush=True)
        elif cached:
            print(f"[INFO] モデルキャッシュ確認: {self._model_name}", flush=True)
        else:
            print(f"[INFO] モデルをHuggingFaceからダウンロード中: {self._model_name}", flush=True)
            print("[INFO] （初回は数百MBのダウンロードが必要です。ネットワーク速度により数分かかります）", flush=True)
            # ダウンロードのみ実行（MLXへのロードはしない）
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=self._model_name)

        print("[INFO] モデルファイル準備完了", flush=True)

    def transcribe(
        self,
        audio: np.ndarray,
        prompt: str = "",
        language: str = DEFAULT_LANGUAGE,
    ) -> str:
        if audio.size == 0:
            return ""
        self._call_count += 1
        duration = audio.size / 16000
        print(f"[DEBUG] transcribe呼び出し #{self._call_count} (音声長: {duration:.1f}秒)", flush=True)
        result = self._transcribe(
            audio,
            path_or_hf_repo=self._model_name,
            initial_prompt=prompt,
            language=language,
            verbose=None,
        )
        return result.get("text", "").strip()
