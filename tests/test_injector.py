"""Injector のテスト — 直接キー入力 + クリップボード方式"""
import time

import pytest

from pynput.keyboard import Key

from kikitori.injector import Injector

class FakeClipboard:
    def __init__(self, initial: str | None = None):
        self.copied = initial

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
        """すべてのテキストがクリップボード経由 Cmd+V で注入される"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("hi")

        # クリップボード経由で注入
        assert clip.copied == "hi"
        # Cmd+V が呼ばれる
        has_cmd_v = any(
            ev == ("press", "v") for ev in ctrl.events
        )
        assert has_cmd_v, "Cmd+V が呼ばれた"

    def test_inject_short_text_backs_up_to_clipboard(self):
        """クリップボード経由注入後に元のクリップボードが復元される"""
        clip = FakeClipboard(initial="original content")
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("backup")

        # 注入時にバックアップがセットされる
        assert clip.copied == "backup"
        # restore スレッドが完了するのを待つ
        import time
        time.sleep(0.1)
        # 復元された
        assert clip.copied == "original content"

    def test_inject_preserves_empty_clipboard(self):
        """元のクリップボードが空（非テキスト）の場合、復元しない"""
        clip = FakeClipboard(initial="")  # 空クリップボード（画像など）
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("hello")

        # 注入後は "hello" のまま（復元スレッドが開始されない）
        import time
        time.sleep(0.1)  # 十分待っても変わらない
        assert clip.copied == "hello", "空クリップボードは復元されない（非テキスト保護）"

    def test_rapid_inject_no_clipboard_corruption(self):
        """高速連続注入でクリップボードが破壊されない。世代管理で復元を適切にスキップする。"""
        clip = FakeClipboard(initial="original")
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)
        import time

        # 1回目の注入
        inj.inject("first")
        assert clip.copied == "first"
        gen_after_first = inj._restore_generation

        # 即座に2回目の注入（1回目の復元スレッドが待機中）
        inj.inject("second")
        assert clip.copied == "second"
        gen_after_second = inj._restore_generation
        assert gen_after_second > gen_after_first

        # 両方の復元スレッドが完了するのを待つ
        time.sleep(0.1)

        # 2回目の復元のみ有効 → "original" に戻る（1回目の復元はスキップされる）
        # 1回目の復元は世代不一致でスキップされるため
        assert clip.copied == "original", (
            f"Expected 'original' but got '{clip.copied}'. "
            f"1st gen={gen_after_first}, 2nd gen={gen_after_second}"
        )

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
        """閾値にかかわらずクリップボード経由で注入"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        text = "12345"  # ちょうど5文字
        inj.inject(text)

        # クリップボード経由で注入される
        assert clip.copied == text
        has_cmd_v = any(
            ev == ("press", "v") for ev in ctrl.events
        )
        assert has_cmd_v

    def test_inject_boundary_exceeds(self):
        """常にクリップボード方式を使用（type()は呼ばれない）"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        text = "123456"  # 6文字
        inj.inject(text)

        assert clip.copied == text
        assert ctrl.typed == []  # type() は呼ばれない

    def test_inject_custom_threshold(self):
        """常にクリップボード経由で注入（閾値パラメータは削除済み）"""
        clip = FakeClipboard()
        ctrl = FakeController()
        inj = Injector(controller=ctrl, clipboard=clip)

        inj.inject("1234567890")  # ちょうど10文字
        # クリップボード経由で注入される
        assert clip.copied == "1234567890"
        has_cmd_v = any(
            ev == ("press", "v") for ev in ctrl.events
        )
        assert has_cmd_v

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
