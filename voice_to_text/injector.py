"""クリップボード経由テキスト入力"""
import time

import pyperclip
from pynput.keyboard import Controller, Key


class Injector:
    def __init__(self, controller=None, clipboard=None):
        self._controller = controller or Controller()
        self._clipboard = clipboard or pyperclip

    def inject(self, text: str, max_wait: float = 1.0):
        if not text:
            return
        self._clipboard.copy(text)
        # クリップボード反映をポーリングで待つ（最大1秒）
        start = time.monotonic()
        while time.monotonic() - start < max_wait:
            try:
                if self._clipboard.paste() == text:
                    break
            except Exception:
                pass
            time.sleep(0.01)
        try:
            self._controller.press(Key.cmd_l)
            self._controller.press("v")
            self._controller.release("v")
            self._controller.release(Key.cmd_l)
        except Exception as e:
            print(f"[WARN] pynput での送信に失敗: {e}")
