"""クリップボード経由テキスト入力"""
import threading

import pyperclip

from kikitori.config import BENCHMARK_MODE, DEBUG

class Injector:
    """テキスト注入クラス。

    常にクリップボード経由 Cmd+V で注入し、注入後に元のクリップボードを復元する。
    """

    def __init__(self, controller=None, clipboard=None):
        if controller is not None:
            self._controller = controller
        else:
            from pynput.keyboard import Controller
            self._controller = Controller()
        self._clipboard = clipboard or pyperclip
        self._restore_generation = 0
        self._restore_lock = threading.Lock()
        self._pending_original = ""

    def inject(self, text: str):
        if DEBUG: print(f"[DEBUG] Injector.inject: text='{text}' (len={len(text)})", flush=True)
        if not text:
            if DEBUG: print("[DEBUG] Injector.inject: empty text, skipping", flush=True)
            return

        self._inject_via_clipboard(text)

    def _inject_via_clipboard(self, text: str):
        """クリップボード経由 Cmd+V でテキストを注入する。

        注入後に元のクリップボードを非同期で復元する。
        連続注入時は復元を統合し、ユーザー本来のクリップボード内容を保護する。
        """
        import time as _time
        from pynput.keyboard import Key
        t0 = _time.perf_counter()

        # 元のクリップボードを保存（初回注入時のみ）
        with self._restore_lock:
            if self._restore_generation == 0:
                try:
                    self._pending_original = self._clipboard.paste()
                except Exception:
                    self._pending_original = ""
            self._restore_generation += 1
            gen = self._restore_generation
            original = self._pending_original

        if DEBUG: print(f"[DEBUG] _inject_via_clipboard: copying '{text[:50]}{'...' if len(text)>50 else ''}' to clipboard", flush=True)
        self._clipboard.copy(text)

        try:
            with self._controller.pressed(Key.cmd_l):
                self._controller.press("v")
                self._controller.release("v")
            if DEBUG: print("[DEBUG] _inject_via_clipboard: Cmd+V sent", flush=True)
        except Exception as e:
            print(f"[WARN] pynput での送信に失敗: {e}")

        # Cmd+V が処理された後で元のクリップボードを復元（非同期）
        # 元が空の場合は復元しない（画像など非テキストクリップボードを保護）
        if original:
            threading.Thread(
                target=self._restore_clipboard,
                args=(original, gen),
                daemon=True,
            ).start()

        if BENCHMARK_MODE:
            elapsed = (_time.perf_counter() - t0) * 1000
            print(f"[BENCH] inject_clipboard: {elapsed:.1f}ms "
                  f"(text_len={len(text)})", flush=True)

    def _restore_clipboard(self, original: str, generation: int) -> None:
        """元のクリップボード内容を復元する（専用スレッドで実行）。

        次回の注入が開始されていた場合（世代が進んでいる場合）は復元をスキップし、
        最後の注入だけが復元を実行する。これにより連続注入時のクリップボード破壊を防ぐ。
        """
        import time as _time
        _time.sleep(0.05)  # Cmd+V が処理されるのを待つ

        with self._restore_lock:
            if generation != self._restore_generation:
                return  # 新しい注入が既に開始されている
            # 復元が完了したらリセット
            self._restore_generation = 0
            self._pending_original = ""

        try:
            self._clipboard.copy(original)
        except Exception:
            pass
