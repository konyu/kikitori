"""音声認識（mlx-whisper ラッパー）"""
from pathlib import Path
from typing import Callable

import numpy as np

from kikitori.config import DEBUG, DEFAULT_LANGUAGE


def _default_prepare_model(model_name: str) -> str:
    """デフォルトのモデル準備: HuggingFace キャッシュ確認・ダウンロード。

    実際の MLX モデルロードは初回 transcribe() 呼び出し時に
    mlx_whisper が pynput スレッド内で行う（GPU Stream の制約のため）。
    ここでは HuggingFace 上のモデルファイルの存在確認とダウンロードのみ行う。
    """
    import threading

    model_path = Path(model_name)
    try:
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(repo_id=model_name, filename="config.json")
    except Exception:
        cached = None

    if model_path.exists():
        print(f"[INFO] モデルパス確認: {model_name} (ローカル)", flush=True)
    elif cached:
        print(f"[INFO] モデルキャッシュ確認: {model_name}", flush=True)
    else:
        print("=" * 50, flush=True)
        print(f"[INFO] モデルを HuggingFace からダウンロードします: {model_name}", flush=True)
        print("[INFO] 初回は数百MBのダウンロードが必要です（数分かかります）", flush=True)
        print("[INFO] ダウンロード完了後はアプリを再起動してください", flush=True)
        print("=" * 50, flush=True)

        # tqdm プログレスバーを無効化（Homebrew/バックグラウンド対応）
        import os
        old_disable = os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS")
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

        stop_spinner = threading.Event()

        def _spinner():
            while not stop_spinner.wait(timeout=5.0):
                print("[INFO] モデルダウンロード中...", flush=True)

        t = threading.Thread(target=_spinner, daemon=True)
        t.start()

        try:
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=model_name)
        finally:
            stop_spinner.set()
            t.join(timeout=1.0)
            if old_disable is not None:
                os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = old_disable
            else:
                os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)

        print("=" * 50, flush=True)
        print("[INFO] モデルダウンロードが完了しました", flush=True)
        print("[INFO] アプリを再起動してください:", flush=True)
        print("       brew services restart konyu/kikitori/kikitori", flush=True)
        print("       または killall kikitori && kikitori", flush=True)
        print("=" * 50, flush=True)

    print("[INFO] モデルファイル準備完了", flush=True)
    return model_name


class Transcriber:
    def __init__(
        self,
        model_name: str,
        transcribe_func: Callable = None,
        load_model_func: Callable = None,
    ):
        self._model_name = model_name
        self._transcribe_func = transcribe_func  # None = lazy import
        self._load_model = load_model_func or _default_prepare_model
        self._model = None
        self._call_count = 0  # デバッグ用: transcribe呼び出し回数

    def _get_transcribe_func(self):
        """mlx_whisper の遅延インポート。初回 transcribe 呼び出し時までインポートを遅らせる。"""
        if self._transcribe_func is not None:
            return self._transcribe_func
        import mlx_whisper
        self._transcribe_func = mlx_whisper.transcribe
        return self._transcribe_func

    def load(self):
        """モデルファイルの準備（キャッシュ確認・ダウンロード）。

        実際の MLX モデルロードは、初回 transcribe() 呼び出し時に
        mlx_whisper が pynput スレッド内で行う（GPU Stream の制約のため）。
        ここでは HuggingFace キャッシュの確認のみで、メモリ消費しない。
        """
        self._model = self._load_model(self._model_name)

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = DEFAULT_LANGUAGE,
    ) -> str:
        if audio.size == 0:
            return ""
        self._call_count += 1
        duration = audio.size / 16000
        if DEBUG: print(f"[DEBUG] transcribe呼び出し #{self._call_count} (音声長: {duration:.1f}秒)", flush=True)
        result = self._get_transcribe_func()(
            audio,
            path_or_hf_repo=self._model_name,
            language=language,
            verbose=None,
        )
        return result.get("text", "").strip()
