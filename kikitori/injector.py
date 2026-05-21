"""クリップボード経由テキスト入力"""
import time
import pyperclip
from pynput.keyboard import Controller, Key


class Injector:
    def __init__(self, controller=None, clipboard=None):
        self._controller = controller or Controller()
        self._clipboard = clipboard or pyperclip

    def inject(self, text: str):
        if not text:
            return
        
        # クリップボードへのコピー（少し待機してOS側に確実に反映させる）
        self._clipboard.copy(text)
        time.sleep(0.1)

        try:
            # 修飾キーを確実に押下
            with self._controller.pressed(Key.cmd_l):
                time.sleep(0.05)
                self._controller.press("v")
                time.sleep(0.05)
                self._controller.release("v")
                time.sleep(0.05)
        except Exception as e:
            print(f"[WARN] pynput での送信に失敗: {e}")
