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
    MODEL_NAME,
    SAMPLE_RATE,
)
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
        hotkey: list[str] | None = None,
        on_state_change=None,
    ):
        self._model_name = model_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._prompt = prompt
        self._language = language
        self._max_duration = max_duration
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
            hotkey=self._hotkey_config,
            on_state_change=on_state_change,
        )
        self._listener = None
        self._listener_thread = None

    def load(self):
        print(f"[INFO] モデルを読み込み中: {self._model_name}")
        self._transcriber.load()
        print("[INFO] モデル読み込み完了")

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
        if listener_factory is None:
            listener_factory = lambda on_press, on_release: keyboard.Listener(
                on_press=on_press, on_release=on_release
            )

        self._listener = listener_factory(
            on_press=self._hotkey.on_press,
            on_release=self._hotkey.on_release,
        )
        self._listener.start()
        self._listener_thread = threading.Thread(target=self._listener.join, daemon=True)
        self._listener_thread.start()

    def stop_background(self):
        """バックグラウンドリスナーを停止"""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._listener_thread = None
