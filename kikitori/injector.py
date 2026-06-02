"""クリップボード経由テキスト入力"""
import threading

import pyperclip
from pynput.keyboard import Controller, Key

from kikitori.config import BENCHMARK_MODE


class Injector:
    """テキスト注入クラス。

    常にクリップボード経由 Cmd+V で注入し、注入後に元のクリップボードを復元する。
    """

    def __init__(self, controller=None, clipboard=None, type_threshold: int = 50):
        self._controller = controller or Controller()
        self._clipboard = clipboard or pyperclip
        self._type_threshold = type_threshold

    def inject(self, text: str):
        if not text:
            return

        self._inject_via_clipboard(text)

    def _inject_via_clipboard(self, text: str):
        """クリップボード経由 Cmd+V でテキストを注入する。

        注入後に元のクリップボードを非同期で復元する。
        元のクリップボードが空だった場合（画像・ファイル等の非テキスト）、
        復元をスキップして内容を保護する。
        """
        import time as _time
        t0 = _time.perf_counter()

        # 元のクリップボードを保存
        try:
            original = self._clipboard.paste()
        except Exception:
            original = ""

        self._clipboard.copy(text)

        try:
            with self._controller.pressed(Key.cmd_l):
                self._controller.press("v")
                self._controller.release("v")
        except Exception as e:
            print(f"[WARN] pynput での送信に失敗: {e}")

        # Cmd+V が処理された後で元のクリップボードを復元（非同期）
        # 元が空の場合は復元しない（画像など非テキストクリップボードを保護）
        if original:
            threading.Thread(
                target=self._restore_clipboard,
                args=(original, self._clipboard),
                daemon=True,
            ).start()

        if BENCHMARK_MODE:
            elapsed = (_time.perf_counter() - t0) * 1000
            print(f"[BENCH] inject_clipboard: {elapsed:.1f}ms "
                  f"(text_len={len(text)})", flush=True)

    @staticmethod
    def _restore_clipboard(original: str, clipboard=None) -> None:
        """元のクリップボード内容を復元する（専用スレッドで実行）。"""
        import time as _time
        _time.sleep(0.05)  # Cmd+V が処理されるのを待つ
        try:
            cb = clipboard if clipboard is not None else pyperclip
            cb.copy(original)
        except Exception:
            pass
