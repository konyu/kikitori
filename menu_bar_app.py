#!/usr/bin/env python3
"""macOS メニューバー常駐型 Kikitori アプリ（ターミナル実行推奨）"""
import os
import threading
from pathlib import Path

import rumps
import yaml

from kikitori.app import App
from kikitori.config import DEFAULT_HOTKEY, DEFAULT_LANGUAGE, DEFAULT_PROMPT, MIN_DURATION_MS, MODEL_NAME, SAMPLE_RATE
from kikitori.hotkey_manager import resolve_hotkey


SETTINGS_PATH = Path.home() / ".kikitori_settings.yaml"


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            return yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
    return {}


def save_settings(settings):
    try:
        SETTINGS_PATH.write_text(
            yaml.dump(settings, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except Exception:
        pass


class KikitoriStatusBarApp(rumps.App):
    def __init__(self):
        super().__init__("🎤", title="Kikitori", quit_button=None)

        self._settings = load_settings()
        self._language = self._settings.get("language", DEFAULT_LANGUAGE)
        self._prompt = self._settings.get("prompt", DEFAULT_PROMPT)
        self._hotkey = self._settings.get("hotkey", DEFAULT_HOTKEY)
        self._min_duration_ms = self._settings.get("min_duration_ms", MIN_DURATION_MS)

        # Core app with state-change callback
        self._app = App(
            language=self._language,
            prompt=self._prompt,
            hotkey=self._hotkey,
            min_duration_ms=self._min_duration_ms,
            on_state_change=self._on_core_state_change,
        )

        # Menu items
        self._status_item = rumps.MenuItem("○ 待機中")
        self._language_item = rumps.MenuItem(f"言語: {self._language}")
        self._prompt_item = rumps.MenuItem(self._prompt_preview(self._prompt))
        self._prompt_item.set_callback(None)
        self._updated_item = rumps.MenuItem("最終更新: --")
        self._updated_item.set_callback(None)
        self._model_item = rumps.MenuItem(f"モデル: {MODEL_NAME}")
        self._model_item.set_callback(None)
        self._model_loading_item = rumps.MenuItem("モデルを読み込み中...")
        self._model_loading_item.set_callback(None)

        self._hotkey_item = rumps.MenuItem(f"ホットキー: {' + '.join(self._hotkey)}")
        self._hotkey_item.set_callback(None)

        # 録音開始/停止ボタン（メニューからの手動操作用）
        self._record_toggle_item = rumps.MenuItem("🔴 録音開始", callback=self._toggle_recording)

        self.menu = [
            self._status_item,
            None,
            self._record_toggle_item,
            None,
            self._model_loading_item,
            self._language_item,
            self._prompt_item,
            self._updated_item,
            self._model_item,
            self._hotkey_item,
            None,
            rumps.MenuItem("設定ファイルを開く", callback=self._open_settings),
            None,
            rumps.MenuItem("終了", callback=self._quit_app),
        ]

        # State flags
        self._recording = False
        self._model_ready = False
        self._loading_item_removed = False

        # Pending menu updates (applied in _update_ui for thread safety)
        self._pending_language = None
        self._pending_prompt = None
        self._pending_updated = None

        # Polling timer for UI refresh (0.1s)
        self._poll_timer = rumps.Timer(self._update_ui, 0.1)

        # Start background tasks
        self._poll_timer.start()
        threading.Thread(target=self._load_model, daemon=True).start()
        self._app.run_background()

    # ── Background tasks ────────────────────────────────────────────────

    def _load_model(self):
        self._app.load()
        self._model_ready = True
        try:
            rumps.notification(
                "Kikitori",
                "準備完了",
                f"モデルの読み込みが完了しました。{' + '.join(self._hotkey)} で録音開始",
            )
        except RuntimeError:
            pass

    def _on_core_state_change(self, is_recording: bool):
        """Called from hotkey listener thread when recording starts/stops."""
        self._recording = is_recording

    def _prompt_preview(self, prompt: str) -> str:
        """プロンプトをメニュー表示用に短縮"""
        max_len = 30
        text = prompt.replace("\n", " ")
        if len(text) > max_len:
            return f"プロンプト: {text[:max_len]}…"
        return f"プロンプト: {text}" if text else "プロンプト: (未設定)"

    def _start_settings_watcher(self):
        """設定ファイルの変更を監視し、変更があれば自動再読み込み"""
        try:
            self._settings_mtime = os.path.getmtime(SETTINGS_PATH)
        except OSError:
            self._settings_mtime = 0

        def check_settings_change(timer):
            try:
                current_mtime = os.path.getmtime(SETTINGS_PATH)
                if current_mtime != getattr(self, "_settings_mtime", 0):
                    self._settings_mtime = current_mtime
                    self._reload_settings()
            except (OSError, FileNotFoundError):
                pass

        # 既存の watcher があれば停止
        if hasattr(self, "_settings_timer") and self._settings_timer is not None:
            self._settings_timer.stop()
            self._settings_timer = None

        self._settings_timer = rumps.Timer(check_settings_change, 1.0)
        self._settings_timer.start()

    def _reload_settings(self):
        """設定ファイルを再読み込みしてアプリに反映"""
        new_settings = load_settings()
        changed = False
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")

        new_lang = new_settings.get("language", DEFAULT_LANGUAGE)
        if new_lang != self._language:
            self._language = new_lang
            self._app._language = new_lang
            self._app._hotkey._language = new_lang
            self._pending_language = f"言語: {new_lang}"
            changed = True

        new_prompt = new_settings.get("prompt", DEFAULT_PROMPT)
        if new_prompt != self._prompt:
            self._prompt = new_prompt
            self._app._prompt = new_prompt
            self._app._hotkey._prompt = new_prompt
            self._pending_prompt = self._prompt_preview(new_prompt)
            changed = True

        new_min_dur = new_settings.get("min_duration_ms", MIN_DURATION_MS)
        if new_min_dur != self._min_duration_ms:
            self._min_duration_ms = new_min_dur
            self._app._min_duration_ms = new_min_dur
            self._app._hotkey._min_duration_samples = int(new_min_dur / 1000 * SAMPLE_RATE)
            changed = True

        new_hotkey = new_settings.get("hotkey", DEFAULT_HOTKEY)
        if new_hotkey != self._hotkey:
            self._hotkey = new_hotkey
            self._app._hotkey_config = new_hotkey
            self._app._hotkey.update_hotkey(new_hotkey)
            self._hotkey_item.title = f"ホットキー: {' + '.join(self._hotkey)}"
            changed = True

        if changed:
            self._settings = new_settings
            self._pending_updated = f"最終更新: {now}"
            self._flash_icon("✅")
            try:
                rumps.notification(
                    "Kikitori",
                    "設定を更新しました",
                    f"言語: {self._language} / {self._prompt_preview(self._prompt)}",
                )
            except RuntimeError:
                pass

    def _flash_icon(self, icon: str, duration: float = 1.5):
        """一時的にアイコンを変更して視覚的フィードバックを与える"""
        original = self.title
        # 録音中なら 🔴 のままにする
        if original == "🔴":
            return
        self.title = icon
        def restore(timer):
            if self.title == icon:
                self.title = "🎤"
        timer = rumps.Timer(restore, duration)
        timer.start()

    def _update_ui(self, timer):
        """Called on main thread by rumps.Timer."""
        is_recording = self._app._hotkey.is_recording()

        # Update icon
        self.title = "🔴" if is_recording else "🎤"

        # Update status text
        status = "● 録音中..." if is_recording else "○ 待機中"
        if self._status_item.title != status:
            self._status_item.title = status

        # Update record toggle button label
        toggle_label = "⏹ 録音停止" if is_recording else "🔴 録音開始"
        if self._record_toggle_item.title != toggle_label:
            self._record_toggle_item.title = toggle_label

        # Apply pending settings updates
        if self._pending_language is not None:
            self._language_item.title = self._pending_language
            self._pending_language = None
        if self._pending_prompt is not None:
            self._prompt_item.title = self._pending_prompt
            self._pending_prompt = None
        if self._pending_updated is not None:
            self._updated_item.title = self._pending_updated
            self._pending_updated = None

        # Update model loading indicator
        if self._model_ready and not self._loading_item_removed:
            title = self._model_loading_item.title
            if title in self.menu:
                self.menu.pop(title)
            self._loading_item_removed = True

    # ── Menu actions ────────────────────────────────────────────────────

    def _toggle_recording(self, _):
        """メニューから録音開始/停止"""
        if self._app._hotkey.is_recording():
            self._app._hotkey.stop_recording()
        else:
            self._app._hotkey.start_recording()

    def _open_settings(self, _):
        """設定ファイルをデフォルトエディタで開く（初回はマニュアル付きで生成）"""
        if not SETTINGS_PATH.exists():
            default_yaml = f"""# Kikitori 設定ファイル
#
# hotkey: 同時押ししたいキーを配列で指定
#   例: ["option"], ["f13"], ["ctrl", "alt"], ["cmd", "shift", "a"]
#
# 利用可能なキー:
#   修飾キー: ctrl, alt (option), cmd (command), shift
#   特殊キー: esc, space, tab, enter, backspace, delete,
#            caps_lock, home, end, page_up, page_down,
#            up, down, left, right
#   Fキー: f1 〜 f20
#   英数字: a 〜 z, 0 〜 9

language: {self._language}
prompt: "{self._prompt}"
hotkey:
"""
            for k in self._hotkey:
                default_yaml += f"  - {k}\n"
            default_yaml += f"min_duration_ms: {self._min_duration_ms}\n"
            SETTINGS_PATH.write_text(default_yaml, encoding="utf-8")

        import subprocess
        subprocess.Popen(["open", str(SETTINGS_PATH)])
        self._start_settings_watcher()

    def _quit_app(self, _):
        self._app.stop_background()
        self._poll_timer.stop()
        if hasattr(self, "_settings_timer") and self._settings_timer is not None:
            self._settings_timer.stop()
            self._settings_timer = None
        rumps.quit_application()


if __name__ == "__main__":
    KikitoriStatusBarApp().run()
