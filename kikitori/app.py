"""アプリケーション統合エントリポイント"""
import threading

from pynput import keyboard

from kikitori.audio_buffer import AudioBuffer
from kikitori.config import (
    CHANNELS,
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    DEFAULT_PROMPT,
    MAX_DURATION,
    MIN_DURATION_MS,
    MODEL_NAME,
    SAMPLE_RATE,
    SILENCE_RMS_THRESHOLD,
)
from kikitori.glossary import Glossary
from kikitori.hotkey_manager import HotkeyManager
from kikitori.injector import Injector
from kikitori.recorder import Recorder
from kikitori.transcriber import Transcriber


class App:
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        prompt: str = DEFAULT_PROMPT,
        language: str = DEFAULT_LANGUAGE,
        max_duration: float = MAX_DURATION,
        min_duration_ms: float = MIN_DURATION_MS,
        hotkey: list[str] | None = None,
        on_state_change=None,
        glossary: "Glossary | None" = None,
        silence_rms_threshold: float = SILENCE_RMS_THRESHOLD,
    ):
        self._model_name = model_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._prompt = prompt
        self._language = language
        self._max_duration = max_duration
        self._min_duration_ms = min_duration_ms
        self._silence_rms_threshold = silence_rms_threshold
        self._hotkey_config = hotkey if hotkey is not None else DEFAULT_HOTKEY

        self._buffer = AudioBuffer()
        self._recorder = Recorder(self._buffer, sample_rate, channels)
        self._transcriber = Transcriber(model_name)
        self._injector = Injector()
        self._hotkey = HotkeyManager(
            self._recorder,
            self._transcriber,
            self._injector,
            prompt=prompt,
            language=language,
            max_duration=max_duration,
            min_duration_ms=min_duration_ms,
            hotkey=self._hotkey_config,
            on_state_change=on_state_change,
            glossary=glossary,
            silence_rms_threshold=silence_rms_threshold,
        )
        self._listener = None
        self._listener_thread = None

    def load(self):
        import sys
        print(f"[INFO] モデルを読み込み中: {self._model_name}", flush=True)
        self._transcriber.load()
        print("[INFO] モデル読み込み完了", flush=True)

    def run(self, listener_factory=None):
        if listener_factory is None:
            listener_factory = lambda on_press, on_release: keyboard.Listener(
                on_press=on_press, on_release=on_release
            )

        print("=" * 50)
        print("Kikitori")
        print("=" * 50)
        print(f"モデル: {self._model_name}")
        print(f"サンプリングレート: {self._sample_rate} Hz")
        print(f"ホットキー: {' + '.join(self._hotkey_config)} (押下中録音 / 解放で出力)")
        print("=" * 50)

        self.load()
        print("[INFO] ホットキーリスナーを開始します。Ctrl+C で終了。")

        with listener_factory(
            on_press=self._hotkey.on_press,
            on_release=self._hotkey.on_release,
        ) as listener:
            listener.join()

    def run_background(self, listener_factory=None):
        """デーモンスレッドでホットキーリスナーを開始（メニューバー用）"""
        import sys
        if listener_factory is None:
            listener_factory = lambda on_press, on_release: keyboard.Listener(
                on_press=on_press, on_release=on_release
            )

        print("[INFO] ホットキーリスナーを開始します...", flush=True)
        self._listener = listener_factory(
            on_press=self._hotkey.on_press,
            on_release=self._hotkey.on_release,
        )
        self._listener.start()
        self._listener_thread = threading.Thread(target=self._listener.join, daemon=True)
        self._listener_thread.start()
        print("[INFO] ホットキーリスナー開始完了。待機中...", flush=True)

    def stop_background(self):
        """バックグラウンドリスナーを停止"""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._listener_thread = None
