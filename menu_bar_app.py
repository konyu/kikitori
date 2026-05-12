#!/usr/bin/env python3
"""macOS メニューバー常駐型 VoiceToText アプリ（rumps + py2app）"""
import json
import os
import threading
from pathlib import Path

import rumps

from voice_to_text.app import App
from voice_to_text.config import DEFAULT_LANGUAGE, DEFAULT_PROMPT, MODEL_NAME


SETTINGS_PATH = Path.home() / ".voice_to_text_settings.json"


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_settings(settings):
    try:
        SETTINGS_PATH.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


class VoiceToTextStatusBarApp(rumps.App):
    def __init__(self):
        super().__init__("🎤", title="VoiceToText", quit_button=None)

        self._settings = load_settings()
        self._language = self._settings.get("language", DEFAULT_LANGUAGE)
        self._prompt = self._settings.get("prompt", DEFAULT_PROMPT)

        # Core app with state-change callback
        self._app = App(
            language=self._language,
            prompt=self._prompt,
            on_state_change=self._on_core_state_change,
        )

        # Menu items
        self._status_item = rumps.MenuItem("○ 待機中")
        self._language_item = rumps.MenuItem(f"言語: {self._language}")
        self._model_item = rumps.MenuItem(f"モデル: {MODEL_NAME}")
        self._model_loading_item = rumps.MenuItem("モデルを読み込み中...")
        self._model_loading_item.set_callback(None)

        self.menu = [
            self._status_item,
            None,
            self._model_loading_item,
            self._language_item,
            self._model_item,
            None,
            rumps.MenuItem("設定ファイルを開く", callback=self._open_settings),
            None,
            rumps.MenuItem("終了", callback=self._quit_app),
        ]

        # State flags
        self._recording = False
        self._model_ready = False
        self._loading_item_removed = False

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
        # .app バンドル外（ターミナル直接実行）では通知が使えない場合がある
        try:
            rumps.notification(
                "VoiceToText",
                "準備完了",
                "モデルの読み込みが完了しました。Ctrl+Option で録音開始",
            )
        except RuntimeError:
            pass

    def _on_core_state_change(self, is_recording: bool):
        """Called from hotkey listener thread when recording starts/stops."""
        self._recording = is_recording

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

        self._settings_timer = rumps.Timer(check_settings_change, 1.0)
        self._settings_timer.start()

    def _reload_settings(self):
        """設定ファイルを再読み込みしてアプリに反映"""
        new_settings = load_settings()
        changed = False

        new_lang = new_settings.get("language", DEFAULT_LANGUAGE)
        if new_lang != self._language:
            self._language = new_lang
            self._app._language = new_lang
            self._app._hotkey._language = new_lang
            self._language_item.title = f"言語: {new_lang}"
            changed = True

        new_prompt = new_settings.get("prompt", DEFAULT_PROMPT)
        if new_prompt != self._prompt:
            self._prompt = new_prompt
            self._app._prompt = new_prompt
            self._app._hotkey._prompt = new_prompt
            changed = True

        if changed:
            self._settings = new_settings
            try:
                rumps.notification(
                    "VoiceToText",
                    "設定を更新しました",
                    f"言語: {self._language}",
                )
            except RuntimeError:
                pass

    def _update_ui(self, timer):
        """Called on main thread by rumps.Timer."""
        is_recording = self._app._hotkey.is_recording()

        # Update icon
        self.title = "🔴" if is_recording else "🎤"

        # Update status text
        status = "● 録音中..." if is_recording else "○ 待機中"
        if self._status_item.title != status:
            self._status_item.title = status

        # Update model loading indicator
        if self._model_ready and not self._loading_item_removed:
            title = self._model_loading_item.title
            if title in self.menu:
                self.menu.pop(title)
            self._loading_item_removed = True

    # ── Menu actions ────────────────────────────────────────────────────

    def _open_settings(self, _):
        """設定ファイルをデフォルトエディタで開く（rumps.Window はフリーズするため）"""
        # 設定ファイルがなければデフォルト値で作成
        if not SETTINGS_PATH.exists():
            default = {
                "language": self._language,
                "prompt": self._prompt,
            }
            save_settings(default)

        # デフォルトエディタで開く
        import subprocess
        subprocess.Popen(["open", str(SETTINGS_PATH)])

        # ファイル変更を監視して自動再読み込み
        self._start_settings_watcher()

    def _quit_app(self, _):
        self._app.stop_background()
        self._poll_timer.stop()
        if hasattr(self, "_settings_timer") and self._settings_timer is not None:
            self._settings_timer.stop()
        rumps.quit_application()


if __name__ == "__main__":
    VoiceToTextStatusBarApp().run()
