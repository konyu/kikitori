"""アプリケーション統合エントリポイント"""
from pynput import keyboard

from voice_to_text.audio_buffer import AudioBuffer
from voice_to_text.config import (
    CHANNELS,
    DEFAULT_LANGUAGE,
    DEFAULT_PROMPT,
    MAX_DURATION,
    MODEL_NAME,
    SAMPLE_RATE,
)
from voice_to_text.hotkey_manager import HotkeyManager
from voice_to_text.injector import Injector
from voice_to_text.recorder import Recorder
from voice_to_text.transcriber import Transcriber


class App:
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        prompt: str = DEFAULT_PROMPT,
        language: str = DEFAULT_LANGUAGE,
        max_duration: float = MAX_DURATION,
    ):
        self._model_name = model_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._prompt = prompt
        self._language = language
        self._max_duration = max_duration

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
        )

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
        print("Voice to Text Injection Tool")
        print("=" * 50)
        print(f"モデル: {self._model_name}")
        print(f"サンプリングレート: {self._sample_rate} Hz")
        print("ホットキー: Ctrl + Option (押下中録音 / 解放で出力)")
        print("=" * 50)

        self.load()
        print("[INFO] ホットキーリスナーを開始します。Ctrl+C で終了。")

        with listener_factory(
            on_press=self._hotkey.on_press,
            on_release=self._hotkey.on_release,
        ) as listener:
            listener.join()
