"""アプリケーション統合エントリポイント"""
import threading

from kikitori.audio_buffer import AudioBuffer
from kikitori.config import (
    APPLE_SPEECH_LOCALE,
    APPLE_SPEECH_ON_DEVICE,
    CHANNELS,
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    DEFAULT_PROMPT,
    DEFAULT_TRANSCRIBER_TYPE,
    MAX_DURATION,
    MIN_DURATION_MS,
    MODEL_NAME,
    SAMPLE_RATE,
    SILENCE_RMS_THRESHOLD,
)
from kikitori.corrections import Corrections
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
        corrections: "Corrections | None" = None,
        silence_rms_threshold: float = SILENCE_RMS_THRESHOLD,
        transcriber_type: str = DEFAULT_TRANSCRIBER_TYPE,
        transcriber: object | None = None,
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
        self._corrections = corrections if corrections is not None else Corrections()

        self._buffer = AudioBuffer()

        # apple_speech 使用時はストリーミング認識用 SpeechAnalyzer を作成
        self._speech_analyzer = None
        self._transcriber_type = transcriber_type
        self._glossary_ref = glossary
        if transcriber is not None:
            self._transcriber = transcriber
        elif transcriber_type == "apple_speech":
            # apple_speech インポートは load() まで遅延（~108ms 節約）
            self._transcriber = None
        else:
            self._transcriber = Transcriber(model_name)

        self._recorder = Recorder(
            self._buffer, sample_rate, channels,
            speech_analyzer=self._speech_analyzer,
        )
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
            corrections=self._corrections,
            silence_rms_threshold=silence_rms_threshold,
            speech_analyzer=self._speech_analyzer,
        )
        self._listener = None
        self._listener_thread = None

    def load(self):
        import sys
        if self._transcriber_type == "apple_speech" and self._transcriber is None:
            from kikitori.apple_speech import SpeechTranscriber, SpeechAnalyzer
            terms = self._glossary_ref.get_terms() if self._glossary_ref else []
            self._transcriber = SpeechTranscriber(
                locale=APPLE_SPEECH_LOCALE, on_device=APPLE_SPEECH_ON_DEVICE,
                contextual_strings=terms,
            )
            self._speech_analyzer = SpeechAnalyzer(
                locale=APPLE_SPEECH_LOCALE, on_device=APPLE_SPEECH_ON_DEVICE,
                contextual_strings=terms,
            )
            self._recorder.set_speech_analyzer(self._speech_analyzer)
            self._hotkey.set_speech_analyzer(self._speech_analyzer)
            self._hotkey.set_transcriber(self._transcriber)
        print(f"[INFO] モデルを読み込み中: {self._model_name}", flush=True)
        self._transcriber.load()
        print("[INFO] モデル読み込み完了", flush=True)
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

