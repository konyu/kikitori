"""PySide6 ベースの Kikitori UI（メニューバー + オーバーレイ）"""

import os
import signal
import sys
import threading
from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from kikitori.app import App
from kikitori.config import (
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    MIN_DURATION_MS,
    MODEL_NAME,
    SILENCE_RMS_THRESHOLD,
)
from kikitori.corrections import CORRECTIONS_PATH, Corrections
from kikitori.corrections_dialog import CorrectionsDialog
from kikitori.glossary import GLOSSARY_PATH, Glossary
from kikitori.glossary_dialog import GlossaryDialog
from kikitori.overlay import VoiceOverlay
from kikitori.settings import (
    SETTINGS_PATH,
    activate_app_by_pid,
    get_frontmost_pid,
    load_settings,
    save_settings,
)
from kikitori.settings_dialog import SettingsDialog


def _set_dock_icon():
    """Dockアイコンを設定する。Homebrew / 開発 両方のパス解決に対応。
    透過背景を白に合成して設定する。"""
    try:
        from AppKit import (
            NSApp,
            NSColor,
            NSCompositingOperationSourceOver,
            NSImage,
            NSRectFill,
        )
        from Foundation import NSMakeRect

        icon_path = Path(__file__).parent.parent / "assets" / "dock-icon.png"
        if not icon_path.exists():
            return
        original = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
        if original is None:
            return

        orig_size = original.size()
        w, h = orig_size.width, orig_size.height

        result = NSImage.alloc().initWithSize_(orig_size)
        result.lockFocus()
        NSColor.whiteColor().set()
        NSRectFill(NSMakeRect(0, 0, w, h))
        source_rect = NSMakeRect(0, 0, w, h)
        dest_rect = NSMakeRect(0, 0, w, h)
        original.drawInRect_fromRect_operation_fraction_(
            dest_rect, source_rect, NSCompositingOperationSourceOver, 1.0
        )
        result.unlockFocus()

        NSApp().setApplicationIconImage_(result)
    except Exception as e:
        print(f"[WARN] Dockアイコン設定に失敗: {e}", file=sys.stderr)


class _ModelLoader(QtCore.QThread):
    """音声認識の初期化をバックグラウンドで実行し、完了をシグナルで通知"""

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
        self.setQuitOnLastWindowClosed(False)  # ダイアログが閉じてもアプリは終了しない

        # Dock非表示: QtがRegularに設定した後、イベントループでAccessoryに上書き
        QtCore.QTimer.singleShot(100, self._hide_from_dock)

        self._settings = load_settings()
        self._language = self._settings.get("language", DEFAULT_LANGUAGE)
        self._hotkey = self._settings.get("hotkey", DEFAULT_HOTKEY)
        self._min_duration_ms = self._settings.get("min_duration_ms", MIN_DURATION_MS)
        self._silence_rms_threshold = self._settings.get("silence_rms_threshold", SILENCE_RMS_THRESHOLD)

        # Glossary（専門用語）
        self._glossary = Glossary()
        self._glossary.load()
        self._corrections = Corrections()
        self._corrections.load()

        # Core app
        self._app = App(
            language=self._language,
            hotkey=self._hotkey,
            min_duration_ms=self._min_duration_ms,
            silence_rms_threshold=self._silence_rms_threshold,
            on_state_change=self._on_core_state_change,
            glossary=self._glossary,
            corrections=self._corrections,
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

        self._settings_action = self._menu.addAction("⚙️ 設定")
        self._settings_action.triggered.connect(self._open_settings_dialog)

        self._glossary_action = self._menu.addAction("📚 用語集")
        self._glossary_action.triggered.connect(self._open_glossary_dialog)

        self._corrections_action = self._menu.addAction("📝 校正辞書")
        self._corrections_action.triggered.connect(self._open_corrections_dialog)

        self._menu.addSeparator()

        self._quit_action = self._menu.addAction("終了")
        self._quit_action.triggered.connect(self._quit_app)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        # Model loader
        self._loader = _ModelLoader(self._app)
        self._loader.loaded.connect(self._on_model_loaded)
        self._loader.failed.connect(self._on_model_failed)
        self._loader.start()

        # Recording state
        self._recording = False
        self._waveform_timer = QtCore.QTimer(self)
        self._waveform_timer.timeout.connect(self._update_waveform)

        # Connect signal to slot for thread-safe UI updates
        self._recording_state_changed.connect(self._update_recording_state)

    def _hide_from_dock(self):
        """Dockに表示されないようにする（macOS専用）"""
        try:
            from AppKit import (
                NSApplicationActivationPolicyAccessory,
                NSApplicationActivationPolicyRegular,
            )

            # QtがRegularに設定した後、Accessoryに上書き
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, lambda: self._set_activation_policy(NSApplicationActivationPolicyAccessory))
        except Exception:
            pass

    def _set_activation_policy(self, policy):
        try:
            from AppKit import NSApp
            NSApp().setActivationPolicy_(policy)
        except Exception:
            pass

    def _set_tray_icon_idle(self):
        """待機中アイコンを設定"""
        icon_path = Path(__file__).parent.parent / "assets" / "icon-idle.png"
        if icon_path.exists():
            icon = QtGui.QIcon(str(icon_path))
            icon.setIsMask(True)
            self._tray.setIcon(icon)

    def _on_model_loaded(self):
        """音声認識の準備完了時"""
        print("[INFO] 音声認識の準備完了", flush=True)
        self._status_action.setText("○ 待機中")
        import threading
        threading.Thread(target=self._app.run, daemon=True).start()

    def _on_model_failed(self, message: str):
        """音声認識の初期化失敗時"""
        print(f"[ERROR] 音声認識の初期化に失敗しました: {message}", flush=True)
        self._status_action.setText("❌ 音声認識の初期化失敗")
        import threading
        threading.Thread(target=self._app.run, daemon=True).start()

    def _on_core_state_change(self, is_recording: bool):
        """録音状態が変化した時に呼ばれる（HotkeyManagerから）"""
        self._recording_state_changed.emit(is_recording)

    def _update_recording_state(self, is_recording: bool):
        """録音状態に応じてUIを更新（メインスレッド）"""
        self._recording = is_recording
        if is_recording:
            # 録音開始
            self._record_action.setText("⏹ 録音停止")
            self._status_action.setText("🔴 録音中...")
            self._overlay.show_overlay()
            self._waveform_timer.start(50)

            # OSのマイクインジケータが表示された後に、アイコンを再セットして表示を維持させる
            QtCore.QTimer.singleShot(500, self._set_tray_icon_idle)
        else:
            # 停止時
            self._set_tray_icon_idle()
            self._record_action.setText("🔴 録音開始")
            self._status_action.setText("○ 待機中")
            self._overlay.hide_overlay()
            self._waveform_timer.stop()

    def _update_waveform(self):
        """波形アニメーションを更新"""
        if self._recording:
            # バッファから直近の振幅を取得してオーバーレイに渡す
            amplitudes = self._app._buffer.get_recent_amplitudes(n_bars=36)
            self._overlay.update_amplitudes(amplitudes)
        self._overlay.update()

    def _toggle_recording(self):
        """メニューから録音開始/停止"""
        if self._app._hotkey.is_recording():
            self._app._hotkey.stop_recording()
        else:
            self._app._hotkey.start_recording()

    def _on_tray_activated(self, reason):
        """トレイアイコンクリック時"""
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_recording()

    def _open_settings_dialog(self):
        """設定ダイアログを開く"""
        from kikitori.settings import load_settings

        fresh = load_settings()
        current = {
            "language": self._language,
            "hotkey": list(self._hotkey),
            "min_duration_ms": self._min_duration_ms,
            "silence_rms_threshold": self._silence_rms_threshold,
        }
        self._dialog = SettingsDialog(current, parent=None)
        result = self._dialog.exec()
        if result == QtWidgets.QDialog.DialogCode.Accepted:
            if self._dialog.reset_requested:
                self._reload_settings()
            else:
                settings = self._dialog._collect_values()
                self._on_settings_changed(settings)
        self._dialog = None

    def _on_settings_changed(self, settings: dict):
        """SettingsDialog からの変更通知を受け取り、即時反映する。"""
        self._language = settings.get("language", self._language)
        self._hotkey = settings.get("hotkey", self._hotkey)
        self._min_duration_ms = settings.get("min_duration_ms", self._min_duration_ms)
        self._silence_rms_threshold = settings.get("silence_rms_threshold", self._silence_rms_threshold)

        # 内部状態に即時反映
        self._app._language = self._language
        self._app._hotkey._language = self._language
        self._app._hotkey.update_hotkey(self._hotkey)
        self._app._hotkey._min_duration_samples = int(
            self._min_duration_ms / 1000 * 16000
        )
        self._app._hotkey._silence_rms_threshold = self._silence_rms_threshold

        # 設定ファイルに保存（内部キャッシュも更新）
        self._settings = {
            "language": self._language,
            "hotkey": self._hotkey,
            "min_duration_ms": self._min_duration_ms,
            "silence_rms_threshold": self._silence_rms_threshold,
        }
        save_settings(self._settings)

        print(
            f"[INFO] 設定を更新しました: language={self._language}, hotkey={' + '.join(self._hotkey)}, min_duration_ms={self._min_duration_ms}",
            flush=True,
        )

    def _open_glossary_dialog(self):
        """キーワード管理ダイアログを開く。"""
        self._dialog = GlossaryDialog(self._glossary)
        result = self._dialog.exec()
        if result == QtWidgets.QDialog.DialogCode.Accepted:
            self._reload_glossary()
        self._dialog = None

    def _reload_glossary(self):
        """Glossary を再読み込みし、内部状態を更新する。"""
        self._glossary.load()
        kw_count = len(self._glossary.get_terms())
        # glossary は参照で共有されているため load() だけで即時反映される
        print(f"[INFO] キーワードを再読み込みしました: {kw_count}件", flush=True)

    def _open_corrections_dialog(self):
        """校正辞書管理ダイアログを開く。"""
        self._dialog = CorrectionsDialog(self._corrections)
        result = self._dialog.exec()
        if result == QtWidgets.QDialog.DialogCode.Accepted:
            self._reload_corrections()
        self._dialog = None

    def _reload_corrections(self):
        """Corrections を再読み込みし、内部状態を更新する。"""
        self._corrections.load()
        corr_count = len(self._corrections.get_items())
        print(f"[INFO] 校正辞書を再読み込みしました: {corr_count}件", flush=True)

    def _reload_settings(self):
        try:
            settings = load_settings()
        except Exception:
            settings = {}

        if not settings:
            from kikitori.config import (
                DEFAULT_HOTKEY,
                DEFAULT_LANGUAGE,
                MIN_DURATION_MS,
                SILENCE_RMS_THRESHOLD,
            )
            new_lang = DEFAULT_LANGUAGE
            new_hotkey = list(DEFAULT_HOTKEY)
            new_min_dur = MIN_DURATION_MS
            new_silence = SILENCE_RMS_THRESHOLD
        else:
            new_lang = settings.get("language", self._language)
            new_hotkey = settings.get("hotkey", self._hotkey)
            new_min_dur = settings.get("min_duration_ms", self._min_duration_ms)
            new_silence = settings.get("silence_rms_threshold", self._silence_rms_threshold)

        self._language = new_lang
        self._hotkey = new_hotkey
        self._min_duration_ms = new_min_dur
        self._silence_rms_threshold = new_silence

        self._app._language = new_lang
        self._app._hotkey._language = new_lang
        self._app._hotkey.update_hotkey(new_hotkey)
        self._app._hotkey._min_duration_samples = int(new_min_dur / 1000 * 16000)
        self._app._hotkey._silence_rms_threshold = new_silence

        print(
            f"[INFO] 設定ファイル変更を反映しました: language={self._language}, hotkey={' + '.join(self._hotkey)}",
            flush=True,
        )

    def _quit_app(self):
        self._tray.hide()
        self.quit()


def main():
    # SIGINT を graceful に処理
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # macOS で Qt のメタタイプ登録エラーを抑制
    os.environ["QT_MAC_WANTS_LAYER"] = "1"

    app = KikitoriUIApp(sys.argv)

    # Dock アイコン設定
    _set_dock_icon()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
