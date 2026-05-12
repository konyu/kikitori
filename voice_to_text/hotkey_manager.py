"""ホットキー状態管理（Ctrl + Option）"""
import threading

from pynput.keyboard import Key

from voice_to_text.config import DEFAULT_LANGUAGE, MAX_DURATION
from voice_to_text.injector import Injector
from voice_to_text.recorder import Recorder
from voice_to_text.transcriber import Transcriber


class HotkeyManager:
    def __init__(
        self,
        recorder: Recorder,
        transcriber: Transcriber,
        injector: Injector,
        prompt: str = "",
        language: str = DEFAULT_LANGUAGE,
        max_duration: float = MAX_DURATION,
        timer_factory=None,
    ):
        self._recorder = recorder
        self._transcriber = transcriber
        self._injector = injector
        self._prompt = prompt
        self._language = language
        self._max_duration = max_duration
        self._timer_factory = timer_factory or threading.Timer
        self._timer = None
        self._ctrl_pressed = False
        self._alt_pressed = False
        self._is_recording = False

    def _start_auto_stop_timer(self):
        self._cancel_auto_stop_timer()
        self._timer = self._timer_factory(self._max_duration, self._on_auto_stop)
        self._timer.start()

    def _cancel_auto_stop_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_auto_stop(self):
        if not self._is_recording:
            return
        self._is_recording = False
        audio = self._recorder.stop()
        if audio.size > 0:
            text = self._transcriber.transcribe(
                audio, prompt=self._prompt, language=self._language
            )
            self._injector.inject(text)
        else:
            print("[INFO] 録音データが空です")
        # キーがまだ押されていれば再録音、そうでなければタイマーをクリア
        if self._ctrl_pressed and self._alt_pressed:
            self._is_recording = True
            self._recorder.start()
            self._start_auto_stop_timer()
        else:
            self._timer = None

    def on_press(self, key):
        if key == Key.ctrl_l:
            self._ctrl_pressed = True
        elif key == Key.alt:
            self._alt_pressed = True
        else:
            return

        if self._ctrl_pressed and self._alt_pressed and not self._is_recording:
            self._is_recording = True
            self._recorder.start()
            self._start_auto_stop_timer()

    def on_release(self, key):
        was_recording = self._is_recording

        if key == Key.ctrl_l:
            self._ctrl_pressed = False
        elif key == Key.alt:
            self._alt_pressed = False
        else:
            return

        if was_recording and not (self._ctrl_pressed and self._alt_pressed):
            self._is_recording = False
            self._cancel_auto_stop_timer()
            audio = self._recorder.stop()
            if audio.size > 0:
                text = self._transcriber.transcribe(
                    audio, prompt=self._prompt, language=self._language
                )
                self._injector.inject(text)
            else:
                print("[INFO] 録音データが空です")
