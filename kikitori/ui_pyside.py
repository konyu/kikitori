"""PySide6 ベースの Kikitori UI（メニューバー + オーバーレイ）"""
import os
import sys
import threading
from pathlib import Path

import numpy as np
import yaml
from PySide6 import QtCore, QtGui, QtWidgets

from kikitori.app import App
from kikitori.config import (
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    DEFAULT_PROMPT,
    MIN_DURATION_MS,
    MODEL_NAME,
)
from kikitori.overlay import VoiceOverlay

SETTINGS_PATH = Path.home() / ".kikitori_settings.yaml"


def _get_frontmost_pid() -> int | None:
    """現在フォーカスされているアプリケーションのPIDを取得する。"""
    try:
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return int(app.processIdentifier())
    except Exception:
        return None


def _activate_app_by_pid(pid: int) -> bool:
    """指定したPIDのアプリケーションをアクティブにする。"""
    try:
        from AppKit import NSRunningApplication
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is None:
            return False
        NSApplicationActivateAllWindows = 1 << 0
        NSApplicationActivateIgnoringOtherApps = 1 << 1
        app.activateWithOptions_(NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps)
        return True
    except Exception:
        return False


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


class _ModelLoader(QtCore.QThread):
    """モデル読み込みをバックグラウンドで実行し、完了をシグナルで通知"""

    loaded = QtCore.Signal()
    failed = QtCore.Signal(str)

    def __init__(self, app: App):
        super().__init__()
        self._app = app

    def run(self):
        try:
            self._app.load()
            self.loaded.emit()
        except Exception as e:
            self.failed.emit(str(e))


class KikitoriUIApp(QtWidgets.QApplication):
    """PySide6 ベースの Kikitori アプリケーション"""

    _recording_state_changed = QtCore.Signal(bool)

    def __init__(self, argv):
        super().__init__(argv)

        self.setApplicationName("Kikitori")

        self._settings = load_settings()
        self._language = self._settings.get("language", DEFAULT_LANGUAGE)
        self._prompt = self._settings.get("prompt", DEFAULT_PROMPT)
        self._hotkey = self._settings.get("hotkey", DEFAULT_HOTKEY)
        self._min_duration_ms = self._settings.get("min_duration_ms", MIN_DURATION_MS)

        # Core app
        self._app = App(
            language=self._language,
            prompt=self._prompt,
            hotkey=self._hotkey,
            min_duration_ms=self._min_duration_ms,
            on_state_change=self._on_core_state_change,
        )

        # Overlay
        self._overlay = VoiceOverlay()

        # System tray
        self._tray = QtWidgets.QSystemTrayIcon(self)
        self._tray.setToolTip("Kikitori")
        self._set_tray_icon_idle()

        # Menu
        self._menu = QtWidgets.QMenu()

        self._status_action = self._menu.addAction("○ 待機中")
        self._status_action.setEnabled(False)

        self._menu.addSeparator()

        self._record_action = self._menu.addAction("🔴 録音開始")
        self._record_action.triggered.connect(self._toggle_recording)

        self._menu.addSeparator()

        self._model_action = self._menu.addAction("モデルを読み込み中...")
        self._model_action.setEnabled(False)

        self._lang_action = self._menu.addAction(f"言語: {self._language}")
        self._lang_action.setEnabled(False)

        self._hotkey_action = self._menu.addAction(f"ホットキー: {' + '.join(self._hotkey)}")
        self._hotkey_action.setEnabled(False)

        self._menu.addSeparator()

        open_settings_action = self._menu.addAction("設定ファイルを開く")
        open_settings_action.triggered.connect(self._open_settings)

        self._menu.addSeparator()

        quit_action = self._menu.addAction("終了")
        quit_action.triggered.connect(self._quit_app)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        # macOS: ウィンドウがなくても終了しない + Dock非表示
        self.setQuitOnLastWindowClosed(False)
        try:
            import objc
            NSApplication = objc.lookUpClass("NSApplication")
            ns_app = NSApplication.sharedApplication()
            ns_app.setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory
        except Exception:
            pass

        # State
        self._recording = False
        self._model_ready = False
        self._last_frontmost_pid: int | None = None  # 録音開始時のフォーカスアプリPID

        # Connect signal
        self._recording_state_changed.connect(self._update_recording_state)

        # Overlay update timer (reads audio buffer amplitudes)
        self._wave_timer = QtCore.QTimer(self)
        self._wave_timer.timeout.connect(self._update_waveform)
        self._wave_timer.start(50)  # 20fps

        # Start model loading in background
        self._model_loader = _ModelLoader(self._app)
        self._model_loader.loaded.connect(self._on_model_loaded)
        self._model_loader.failed.connect(self._on_model_failed)
        self._model_loader.start()

        # Settings watcher
        self._settings_mtime = None
        self._settings_timer = QtCore.QTimer(self)
        self._settings_timer.timeout.connect(self._check_settings_change)
        self._settings_timer.start(1000)

    # ── Tray icons ───────────────────────────────────────────────────────

    def _set_tray_icon_idle(self):
        icon = QtGui.QIcon(str(Path(__file__).parent.parent / "assets" / "icon-idle.png"))
        icon.setIsMask(True)  # ダーク/ライトモード自動対応
        self._tray.setIcon(icon)

    def _set_tray_icon_recording(self):
        icon = QtGui.QIcon(str(Path(__file__).parent.parent / "assets" / "icon-recording.png"))
        # 赤いアイコンはマスクモードOFFで色付き表示
        self._tray.setIcon(icon)

    # ── Model loading callbacks ──────────────────────────────────────────

    def _on_model_loaded(self):
        self._model_ready = True
        self._model_action.setText(f"モデル: {MODEL_NAME}")
        self._status_action.setText("○ 待機中")
        self._app.run_background()

    def _on_model_failed(self, message: str):
        self._model_action.setText(f"モデル読み込み失敗")
        print(f"[ERROR] モデル読み込み失敗: {message}", file=sys.stderr)

    # ── Recording state ──────────────────────────────────────────────────

    def _on_core_state_change(self, is_recording: bool):
        # Called from pynput thread → emit signal to switch to Qt thread
        self._recording_state_changed.emit(is_recording)

    def _update_recording_state(self, is_recording: bool):
        self._recording = is_recording
        if is_recording:
            # 録音開始直前にフォーカスされているアプリのPIDを記憶
            self._last_frontmost_pid = _get_frontmost_pid()
            self._status_action.setText("🔴 録音中")
            self._record_action.setText("⏹ 録音停止")
            self._set_tray_icon_recording()
            self._overlay.show_overlay()
        else:
            self._status_action.setText("○ 待機中")
            self._record_action.setText("🔴 録音開始")
            self._set_tray_icon_idle()
            self._overlay.hide_overlay()
            self._overlay.update_amplitudes(np.zeros(30, dtype=np.float32))
            # 録音停止時に元のアプリにフォーカスを戻す
            if self._last_frontmost_pid is not None:
                _activate_app_by_pid(self._last_frontmost_pid)
                self._last_frontmost_pid = None

    def _update_waveform(self):
        if self._recording and self._app._buffer.is_recording():
            amps = self._app._buffer.get_recent_amplitudes()
            self._overlay.update_amplitudes(amps)
        elif self._overlay.isVisible():
            self._overlay.update_amplitudes(np.zeros(30, dtype=np.float32))

    def _toggle_recording(self):
        if self._recording:
            self._app._hotkey.stop_recording()
        else:
            self._app._hotkey.start_recording()

    def _on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_recording()

    # ── Settings ─────────────────────────────────────────────────────────

    def _open_settings(self):
        default_yaml = f"""# Kikitori 設定ファイル
language: {self._language}
prompt: {self._prompt}
hotkey:
"""
        for k in self._hotkey:
            default_yaml += f"  - {k}\n"
        default_yaml += f"min_duration_ms: {self._min_duration_ms}\n"

        if not SETTINGS_PATH.exists():
            try:
                SETTINGS_PATH.write_text(default_yaml, encoding="utf-8")
            except Exception:
                pass

        import subprocess
        subprocess.call(["open", str(SETTINGS_PATH)])

    def _check_settings_change(self):
        if not SETTINGS_PATH.exists():
            return
        try:
            mtime = SETTINGS_PATH.stat().st_mtime
            if self._settings_mtime is None:
                self._settings_mtime = mtime
                return
            if mtime != self._settings_mtime:
                self._settings_mtime = mtime
                self._reload_settings()
        except Exception:
            pass

    def _reload_settings(self):
        try:
            settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            return

        new_lang = settings.get("language", self._language)
        new_prompt = settings.get("prompt", self._prompt)
        new_hotkey = settings.get("hotkey", self._hotkey)
        new_min_dur = settings.get("min_duration_ms", self._min_duration_ms)

        self._language = new_lang
        self._prompt = new_prompt
        self._hotkey = new_hotkey
        self._min_duration_ms = new_min_dur

        self._app._language = new_lang
        self._app._prompt = new_prompt
        self._app._hotkey._prompt = new_prompt
        self._app._hotkey._language = new_lang
        self._app._hotkey.update_hotkey(new_hotkey)
        self._app._hotkey._min_duration_samples = int(new_min_dur / 1000 * 16000)

        self._lang_action.setText(f"言語: {self._language}")
        self._hotkey_action.setText(f"ホットキー: {' + '.join(self._hotkey)}")

        save_settings(settings)

    # ── Quit ─────────────────────────────────────────────────────────────

    def _quit_app(self):
        self._app.stop_background()
        self._tray.hide()
        self.quit()


def main():
    app = KikitoriUIApp(sys.argv)
    sys.exit(app.exec())
