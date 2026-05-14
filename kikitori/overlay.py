"""音声入力中オーバーレイ UI（PySide6）"""
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets


class VoiceOverlay(QtWidgets.QWidget):
    """画面中央下に表示される音声入力中オーバーレイ"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window flags: frameless, always on top, tool window (no dock icon)
        # Note: WindowTransparentForInput is omitted on macOS as it can
        # prevent the window from showing at all in some Qt/macOS versions.
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Size
        self._width = 420
        self._height = 140
        self.setFixedSize(self._width, self._height)

        # Position: center-bottom of primary screen
        self._center_on_screen()

        # Animation timer (30fps)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)

        # Waveform data
        self._amplitudes = np.zeros(30, dtype=np.float32)
        self._idle_phase = 0.0  # for idle animation

        # Colors
        self._bg_color = QtGui.QColor(0, 0, 0, 160)
        self._bar_color = QtGui.QColor(0, 255, 136, 220)
        self._idle_color = QtGui.QColor(100, 100, 100, 120)
        self._text_color = QtGui.QColor(255, 255, 255)

    def _center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self._width) // 2
        y = screen.height() - self._height - 40
        self.move(x, y)

    def update_amplitudes(self, amplitudes: np.ndarray):
        """外部から波形データを更新"""
        if len(amplitudes) > 0:
            self._amplitudes = amplitudes
        self.update()

    def show_overlay(self):
        """フォーカスを奪わずにオーバーレイを表示する"""
        self._center_on_screen()
        self.show()
        self.raise_()
        self.update()

        # macOS: Prevent focus stealing by deactivating our app
        # and configuring the NSWindow to never become key/main
        try:
            import objc
            view = objc.objc_object(c_void_p=int(self.winId()))
            window = view.window()
            if window:
                window.setCanBecomeKeyWindow_(False)
                window.setCanBecomeMainWindow_(False)

            # Deactivate the app so focus returns to the previously active app
            NSRunningApplication = objc.lookUpClass("NSRunningApplication")
            current_app = NSRunningApplication.currentApplication()
            current_app.deactivate()
        except Exception:
            pass

    def hide_overlay(self):
        """確実に非表示にするラッパー"""
        self.hide()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Draw rounded background
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawRoundedRect(rect, 16, 16)

        # Draw waveform bars
        n_bars = len(self._amplitudes)
        if n_bars == 0:
            painter.end()
            return

        bar_width = 6
        bar_gap = 4
        total_width = n_bars * (bar_width + bar_gap) - bar_gap
        start_x = (self._width - total_width) // 2
        bar_area_top = 20
        bar_area_bottom = 85
        bar_area_height = bar_area_bottom - bar_area_top
        center_y = (bar_area_top + bar_area_bottom) // 2

        self._idle_phase += 0.08

        for i, amp in enumerate(self._amplitudes):
            x = start_x + i * (bar_width + bar_gap)

            if amp > 0.02:
                # Active recording: height based on amplitude
                height = max(4, int(bar_area_height * amp))
                color = self._bar_color
            else:
                # Idle: subtle breathing animation
                idle_amp = 0.15 + 0.08 * np.sin(self._idle_phase + i * 0.3)
                height = max(3, int(bar_area_height * idle_amp))
                color = self._idle_color

            y = center_y - height // 2

            # Smooth the color based on amplitude
            if amp > 0.5:
                r = int(0 + (255 - 0) * min((amp - 0.5) * 2, 1))
                g = int(255)
                b = int(136 - 136 * min((amp - 0.5) * 2, 1))
                color = QtGui.QColor(r, g, b, 220)

            painter.setBrush(color)
            painter.drawRoundedRect(x, y, bar_width, height, 3, 3)

        # Draw status text
        painter.setPen(self._text_color)
        font = painter.font()
        font.setPointSize(13)
        font.setWeight(QtGui.QFont.Weight.Medium)
        painter.setFont(font)

        if np.max(self._amplitudes) > 0.02:
            text = "音声入力中..."
        else:
            text = "待機中"

        text_rect = QtCore.QRect(0, bar_area_bottom + 8, self._width, 30)
        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)

        painter.end()
