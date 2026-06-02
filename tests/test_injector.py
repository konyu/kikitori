"""Injector のテスト — 直接キー入力 + クリップボード方式"""
import time

import pytest

from pynput.keyboard import Key

from kikitori.injector import Injector

class FakeClipboard:
    def __init__(self):
        self.copied = None

    def copy(self, text):
        self.copied = text

    def paste(self):
        return self.copied

class FakeController:
    def __init__(self):
        self.events = []
        self.typed = []

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))

    def type(self, text):
        """pynput.Controller.type() のエミュレート。
        各文字の press/release ペアを記録する。"""
        self.typed.append(text)
        for char in text:
            self.events.append(("press", char))
            self.events.append(("release", char))

    def pressed(self, key):
        """with 文用コンテキストマネージャの簡易エミュレート。"""
        return _FakePressedContext(self, key)


class _FakePressedContext:
    def __init__(self, controller, key):
        self._controller = controller
        self._key = key

    def __enter__(self):
        self._controller.press(self._key)

    def __exit__(self, *args):
        self._controller.release(self._key)


class TestInjector:
    def test_inject_empty_text_does_nothing(self):
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("")

        assert clip.copied is None
        assert ctrl.events == []

    def test_inject_short_text_types_directly(self):
        """閾値以下のテキストは直接キー入力される"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("hi")

        # 直接入力された
        assert ctrl.typed == ["hi"]
        # Cmd+V は呼ばれない
        has_cmd_v = any(
            ev == ("press", "v") for ev in ctrl.events
        )
        assert not has_cmd_v, "直接入力モードで Cmd+V が呼ばれた"

    def test_inject_short_text_backs_up_to_clipboard(self):
        """直接入力後にクリップボードへバックアップコピーされる"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("backup")

        assert clip.copied == "backup"

    def test_inject_long_text_uses_clipboard_fallback(self):
        """閾値超過のテキストはクリップボード経由 Cmd+V"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        long_text = "x" * 100  # 50閾値を超える
        inj.inject(long_text)

        # クリップボードにコピーされた
        assert clip.copied == long_text
        # Cmd+V が呼ばれた
        has_cmd_v = any(
            (ev[0] == "press" and ev[1] == "v") or
            (ev[0] == "release" and ev[1] == "v")
            for ev in ctrl.events
        )
        assert has_cmd_v, "長文で Cmd+V が呼ばれなかった"

    def test_inject_fallback_has_no_sleep(self):
        """クリップボード方式に sleep がない"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        start = time.monotonic()
        inj.inject("x" * 100)
        elapsed = time.monotonic() - start

        assert elapsed < 0.01, f"sleep がある（{elapsed:.3f}s）"

    def test_inject_boundary(self):
        """閾値ちょうどでの挙動（直接入力）"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip, type_threshold=5)

        text = "12345"  # ちょうど5文字
        inj.inject(text)

        assert ctrl.typed == [text]

    def test_inject_boundary_exceeds(self):
        """閾値+1でクリップボード方式にフォールバック"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip, type_threshold=5)

        text = "123456"  # 6文字
        inj.inject(text)

        assert clip.copied == text
        assert ctrl.typed == []  # type() は呼ばれない

    def test_inject_custom_threshold(self):
        """コンストラクタで閾値を変更可能"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip, type_threshold=10)

        inj.inject("1234567890")  # ちょうど10文字
        assert ctrl.typed == ["1234567890"]

    def test_inject_key_error_is_caught(self):
        """pynput でのキー送信失敗をハンドリング（直接入力 → クリップボードフォールバック）"""
        class BrokenTypingController:
            def __init__(self):
                self.events = []

            def type(self, text):
                raise RuntimeError("accessibility denied")

            def press(self, key):
                self.events.append(("press", key))

            def release(self, key):
                self.events.append(("release", key))

            def pressed(self, key):
                return _FakePressedContext(self, key)

        clip = FakeClipboard()
        ctrl = BrokenTypingController()
        inj = Injector(controller=ctrl, clipboard=clip)

        # 例外が上がらず、クリップボードフォールバックされる
        inj.inject("test")
        assert clip.copied == "test"
        # Cmd+V が呼ばれた
        has_v = any(ev[1] == "v" for ev in ctrl.events)
        assert has_v, "フォールバックで Cmd+V が呼ばれなかった"
