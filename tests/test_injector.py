"""Injector のテスト — クリップボード経由テキスト入力"""
import time

import pytest

from pynput.keyboard import Key

from voice_to_text.injector import Injector


class FakeClipboard:
    def __init__(self):
        self.copied = None

    def copy(self, text):
        self.copied = text


class FakeController:
    def __init__(self):
        self.events = []

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))


class TestInjector:
    def test_inject_copies_text_and_sends_cmd_v(self):
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("hello", delay=0.01)

        assert clip.copied == "hello"
        assert ctrl.events == [
            ("press", Key.cmd_l),
            ("press", "v"),
            ("release", "v"),
            ("release", Key.cmd_l),
        ]

    def test_inject_empty_text_does_nothing(self):
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("")

        assert clip.copied is None
        assert ctrl.events == []

    def test_inject_respects_delay(self):
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        start = time.monotonic()
        inj.inject("x", delay=0.05)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.05

    def test_inject_key_error_is_caught(self):
        """pynput でのキー送信失敗をハンドリング"""
        class BrokenController:
            def press(self, key):
                raise RuntimeError("accessibility denied")

            def release(self, key):
                pass

        clip = FakeClipboard()
        inj = Injector(controller=BrokenController(), clipboard=clip)
        # 例外が上がらないこと
        inj.inject("test", delay=0.01)
        assert clip.copied == "test"
