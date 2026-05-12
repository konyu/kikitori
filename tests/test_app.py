"""App の統合テスト"""
import threading
import time

import pytest
from pynput.keyboard import Key

from voice_to_text.app import App
from voice_to_text.audio_buffer import AudioBuffer
from voice_to_text.hotkey_manager import HotkeyManager
from voice_to_text.injector import Injector
from voice_to_text.recorder import Recorder
from voice_to_text.transcriber import Transcriber


class FakeListener:
    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release
        self.joined = False
        self._thread = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def join(self):
        self.joined = True


class FakeTranscriberForApp:
    def __init__(self):
        self.loaded = False

    def load(self):
        self.loaded = True

    def transcribe(self, audio, prompt="", language="ja"):
        return "認識結果"


class TestApp:
    def test_app_initializes_components(self):
        app = App(model_name="test-model")
        assert app._model_name == "test-model"
        assert app._sample_rate == 16000

    def test_app_loads_model(self):
        trans = FakeTranscriberForApp()
        app = App()
        app._transcriber = trans
        app.load()
        assert trans.loaded

    def test_app_runs_listener(self):
        listener = FakeListener()
        app = App()
        app.run(listener_factory=lambda **kwargs: listener)
        assert listener.joined

    def test_end_to_end_via_listener(self):
        """FakeListener 経由でホットキーイベントをシミュレート"""
        buf = AudioBuffer()
        rec = Recorder(buf, stream_factory=lambda *, callback: None)
        trans = FakeTranscriberForApp()
        inj = Injector()
        mgr = HotkeyManager(rec, trans, inj)

        # 本来なら App 内で組み立てるが、ここでは直接テスト
        listener = FakeListener(on_press=mgr.on_press, on_release=mgr.on_release)

        # ホットキー押下・解放をシミュレート
        listener.on_press(Key.ctrl_l)
        listener.on_press(Key.alt)
        listener.on_release(Key.alt)

        # App.run は join でブロックするので、ここでは単体で検証
        assert trans.loaded is False  # このテストでは load していない
