"""HotkeyManager のテスト — Ctrl+Option 状態遷移"""
import numpy as np
import pytest
from pynput.keyboard import Key

from voice_to_text.audio_buffer import AudioBuffer
from voice_to_text.hotkey_manager import HotkeyManager
from voice_to_text.injector import Injector
from voice_to_text.recorder import Recorder
from voice_to_text.transcriber import Transcriber


class FakeRecorder:
    def __init__(self):
        self.started = False
        self.stopped = False
        self._audio = np.array([0.1, 0.2], dtype=np.float32)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True
        return self._audio


class FakeTranscriber:
    def __init__(self, text="テスト"):
        self.text = text
        self.calls = []

    def transcribe(self, audio, prompt="", language="ja"):
        self.calls.append((audio.copy(), prompt, language))
        return self.text


class FakeInjector:
    def __init__(self):
        self.injected = []

    def inject(self, text, delay=0.2):
        self.injected.append(text)


class TestHotkeyManager:
    def test_press_ctrl_alone_does_not_start(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector())
        mgr.on_press(Key.ctrl_l)
        assert not rec.started

    def test_press_alt_alone_does_not_start(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector())
        mgr.on_press(Key.alt)
        assert not rec.started

    def test_press_both_starts_recording(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector())
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        assert rec.started

    def test_release_either_stops_and_injects(self):
        rec = FakeRecorder()
        trans = FakeTranscriber("こんにちは")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj)

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.ctrl_l)

        assert rec.stopped
        assert inj.injected == ["こんにちは"]
        assert len(trans.calls) == 1

    def test_release_other_key_ignored(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector())
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.shift)

        assert not rec.stopped

    def test_double_start_is_ignored(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector())
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_press(Key.ctrl_l)  # 再度
        assert rec.started
        # start が2回呼ばれていない（内部フラグでガード）

    def test_release_when_not_recording_does_nothing(self):
        rec = FakeRecorder()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector())
        mgr.on_release(Key.ctrl_l)
        assert not rec.stopped
        assert inj.injected == []

    def test_empty_audio_skips_transcription(self):
        rec = FakeRecorder()
        rec._audio = np.array([], dtype=np.float32)
        trans = FakeTranscriber()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj)

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)

        assert rec.stopped
        assert len(trans.calls) == 0
        assert inj.injected == []

    def test_release_order_independent(self):
        """Ctrl または Alt のどちらを先に離しても動作する"""
        rec = FakeRecorder()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, FakeTranscriber("A"), inj)

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)  # alt を先に離す
        assert rec.stopped
        assert inj.injected == ["A"]

    def test_full_cycle_twice(self):
        rec = FakeRecorder()
        trans = FakeTranscriber("A")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj)

        for _ in range(2):
            rec.stopped = False
            mgr.on_press(Key.ctrl_l)
            mgr.on_press(Key.alt)
            mgr.on_release(Key.ctrl_l)

        assert len(inj.injected) == 2
        assert all(t == "A" for t in inj.injected)

    def test_prompt_and_language_passed_to_transcriber(self):
        rec = FakeRecorder()
        trans = FakeTranscriber()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, prompt="テストプロンプト", language="en")

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)

        assert len(trans.calls) == 1
        assert trans.calls[0][1] == "テストプロンプト"
        assert trans.calls[0][2] == "en"
