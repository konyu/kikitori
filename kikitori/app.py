"""アプリケーション統合エントリポイント"""
import threading

from kikitori.audio_buffer import AudioBuffer
from kikitori.config import (
    APPLE_SPEECH_LOCALE,
    APPLE_SPEECH_ON_DEVICE,
    CHANNELS,
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    MAX_DURATION,
    MIN_DURATION_MS,
    SAMPLE_RATE,
    SILENCE_RMS_THRESHOLD,
)
from kikitori.corrections import Corrections
from kikitori.glossary import Glossary
from kikitori.hotkey_manager import HotkeyManager
from kikitori.injector import Injector
from kikitori.recorder import Recorder


class App:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        language: str = DEFAULT_LANGUAGE,
        max_duration: float = MAX_DURATION,
        min_duration_ms: float = MIN_DURATION_MS,
        hotkey: list[str] | None = None,
        on_state_change=None,
        glossary: "Glossary | None" = None,
        corrections: "Corrections | None" = None,
        silence_rms_threshold: float = SILENCE_RMS_THRESHOLD,
    ):
        self._sample_rate = sample_rate
        self._channels = channels
        self._language = language
        self._max_duration = max_duration
        self._min_duration_ms = min_duration_ms
        self._silence_rms_threshold = silence_rms_threshold
        self._hotkey_config = hotkey if hotkey is not None else DEFAULT_HOTKEY
        self._corrections = corrections if corrections is not None else Corrections()

        self._buffer = AudioBuffer()

        # Apple Speech 使用時はストリーミング認識用 SpeechAnalyzer を load() で作成
        self._speech_analyzer = None
        self._glossary_ref = glossary

        self._recorder = Recorder(
            self._buffer, sample_rate, channels,
            speech_analyzer=self._speech_analyzer,
        )
        self._injector = Injector()
        self._hotkey = HotkeyManager(
            self._recorder,
            self._injector,
            language=language,
            max_duration=max_duration,
            min_duration_ms=min_duration_ms,
            hotkey=self._hotkey_config,
            on_state_change=on_state_change,
            glossary=glossary,
            corrections=self._corrections,
            silence_rms_threshold=silence_rms_threshold,
            speech_analyzer=self._speech_analyzer,
        )
        self._listener = None
        self._listener_thread = None

    def load(self):
        from kikitori.apple_speech import SpeechAnalyzer
        terms = self._glossary_ref.get_terms() if self._glossary_ref else []
        self._speech_analyzer = SpeechAnalyzer(
            locale=APPLE_SPEECH_LOCALE, on_device=APPLE_SPEECH_ON_DEVICE,
            contextual_strings=terms,
        )
        self._recorder.set_speech_analyzer(self._speech_analyzer)
        self._hotkey.set_speech_analyzer(self._speech_analyzer)
        self._speech_analyzer.load()
        self._corrections.load()
        print(f"[INFO] 校正辞書を読み込みました（{len(self._corrections.get_items())} 件）", flush=True)

    def run_background(self, listener_factory=None):
        """ホットキーリスナーをバックグラウンドスレッドで開始する。"""
        if listener_factory is None:
            from pynput import keyboard
            listener_factory = lambda on_press, on_release: keyboard.Listener(
                on_press=on_press, on_release=on_release
            )
        self._listener = listener_factory(
            on_press=self._hotkey.on_press,
            on_release=self._hotkey.on_release,
        )
        self._listener_thread = threading.Thread(
            target=self._listener.start, daemon=True
        )
        self._listener_thread.start()

    def stop_background(self):
        """バックグラウンドのホットキーリスナーを停止する。"""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._listener_thread = None

    def run(self, listener_factory=None):
        if listener_factory is None:
            from pynput import keyboard
            listener_factory = lambda on_press, on_release: keyboard.Listener(
                on_press=on_press, on_release=on_release
            )

        print("=" * 50)
        print("Kikitori")
        print("=" * 50)
        print(f"音声認識: Apple Speech")
        print(f"サンプリングレート: {self._sample_rate} Hz")
        print(f"ホットキー: {' + '.join(self._hotkey_config)} (押下中録音 / 解放で出力)")
        print("=" * 50)

        self.load()
        print("[INFO] ホットキーリスナーを開始します。Ctrl+C で終了。")

        with listener_factory(
            on_press=self._hotkey.on_press,
            on_release=self._hotkey.on_release,
        ) as listener:
            # listener.join() の代わりにメイン RunLoop を駆動する。
            # SFSpeechRecognizer のコールバックはメイン RunLoop で処理されるため
            # ここでポンプしないと認識結果が永遠に返ってこない。
            from Foundation import NSRunLoop, NSDate, NSDefaultRunLoopMode
            while listener.is_alive():
                NSRunLoop.mainRunLoop().runMode_beforeDate_(
                    NSDefaultRunLoopMode,
                    NSDate.dateWithTimeIntervalSinceNow_(0.05),
                )
            listener.join()
