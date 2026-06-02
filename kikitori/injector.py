"""クリップボード経由テキスト入力"""
import pyperclip
from pynput.keyboard import Controller, Key

from kikitori.config import BENCHMARK_MODE


class Injector:
    """テキスト注入クラス。

    短いテキスト（デフォルト50文字以下）は pynput.Controller.type() で
    直接キー入力し、長いテキストはクリップボード経由 Cmd+V で注入する。
    """

    def __init__(self, controller=None, clipboard=None, type_threshold: int = 50):
        self._controller = controller or Controller()
        self._clipboard = clipboard or pyperclip
        self._type_threshold = type_threshold

    def inject(self, text: str):
        if not text:
            return

        if len(text) <= self._type_threshold:
            self._inject_direct(text)
        else:
            self._inject_via_clipboard(text)

    def _inject_direct(self, text: str):
        """pynput.Controller.type() で直接キー入力する。
        入力後にクリップボードへバックアップコピーする。"""
        import time as _time
        t0 = _time.perf_counter()

        try:
            self._controller.type(text)
        except Exception as e:
            print(f"[WARN] pynput での直接入力に失敗: {e}")
            # フォールバック: クリップボード経由
            self._inject_via_clipboard(text)
            return

        # バックアップとしてクリップボードにコピー
        self._clipboard.copy(text)

        if BENCHMARK_MODE:
            elapsed = (_time.perf_counter() - t0) * 1000
            print(f"[BENCH] inject_direct: {elapsed:.1f}ms ("
                  f"text_len={len(text)})", flush=True)

    def _inject_via_clipboard(self, text: str):
        """クリップボード経由 Cmd+V でテキストを注入する（sleep なし）。"""
        import time as _time
        t0 = _time.perf_counter()

        self._clipboard.copy(text)

        try:
            with self._controller.pressed(Key.cmd_l):
                self._controller.press("v")
                self._controller.release("v")
        except Exception as e:
            print(f"[WARN] pynput での送信に失敗: {e}")

        if BENCHMARK_MODE:
            elapsed = (_time.perf_counter() - t0) * 1000
            print(f"[BENCH] inject_clipboard: {elapsed:.1f}ms ("
                  f"text_len={len(text)})", flush=True)
