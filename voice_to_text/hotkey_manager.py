"""ホットキー状態管理（Ctrl + Option）"""
from pynput.keyboard import Key

from voice_to_text.injector import Injector
from voice_to_text.recorder import Recorder
from voice_to_text.transcriber import Transcriber


class HotkeyManager:
    def __init__(self, recorder: Recorder, transcriber: Transcriber, injector: Injector):
        self._recorder = recorder
        self._transcriber = transcriber
        self._injector = injector
        self._ctrl_pressed = False
        self._alt_pressed = False
        self._is_recording = False

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
            audio = self._recorder.stop()
            if audio.size > 0:
                text = self._transcriber.transcribe(audio)
                self._injector.inject(text)
            else:
                print("[INFO] 録音データが空です")
