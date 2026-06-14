"""音声入力中オーバーレイ UI（PySide6）— Aqua Voice スタイル"""
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets


class VoiceOverlay(QtWidgets.QWidget):
    """画面中央下に表示される音声入力中オーバーレイ（Aqua Voice風カプセルUI）"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Aqua Voice 風カプセルサイズ
        self._width = 170
        self._height = 44
        self.setFixedSize(self._width, self._height)

        self._center_on_screen()

        # Animation timer (~30fps)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)

        # Waveform data (12 bars for display)
        self._amplitudes = np.zeros(12, dtype=np.float32)
        self._idle_phase = 0.0

    def _center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self._width) // 2
        y = screen.height() - self._height - 28
        self.move(x, y)

    def update_amplitudes(self, amplitudes: np.ndarray):
        """外部から波形データを更新（任意の長さ → 12本にリサンプル）"""
        if len(amplitudes) == 0:
            self._amplitudes.fill(0.0)
        elif len(amplitudes) == 12:
            self._amplitudes = amplitudes.astype(np.float32)
        else:
            old_x = np.linspace(0, 1, len(amplitudes))
            new_x = np.linspace(0, 1, 12)
            self._amplitudes = np.interp(new_x, old_x, amplitudes).astype(np.float32)
        self.update()

    def show_overlay(self):
        """フォーカスを奪わずにオーバーレイを表示する"""
        self._center_on_screen()
        self.show()
        self.raise_()
        self.update()

        try:
            import objc
            view = objc.objc_object(c_void_p=int(self.winId()))
            window = view.window()
            if window:
                window.setCanBecomeKeyWindow_(False)
                window.setCanBecomeMainWindow_(False)
            NSRunningApplication = objc.lookUpClass("NSRunningApplication")
            current_app = NSRunningApplication.currentApplication()
            current_app.deactivate()
        except Exception:
            pass

    def hide_overlay(self):
        """確実に非表示にする"""
        self.hide()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # ── 背景（カプセル型ピル） ────────────────────────────────────
        bg_rect = QtCore.QRectF(0, 0, self._width, self._height)
        radius = self._height / 2

        path = QtGui.QPainterPath()
        path.addRoundedRect(bg_rect, radius, radius)

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        # 画像に基づくソリッドな暗いグレー背景
        painter.fillPath(path, QtGui.QColor(65, 75, 90, 230))

        # ── 中央寄せレイアウト計算 ────────────────────────────────────
        n_bars = 12
        mic_r = 10
        mic_gap = 14
        bar_w = 4.0

        start_x = 24                              # 左マージン
        mic_x = start_x + mic_r                   # 24 + 10 = 34
        bar_start_x = mic_x + mic_r + mic_gap     # 34 + 10 + 14 = 58
        bar_area_w = self._width - bar_start_x - 24  # 右マージン 24px → 170-58-24 = 88
        bar_gap = (bar_area_w - n_bars * bar_w) / (n_bars - 1) if n_bars > 1 else 0

        # ── 青いマイクインジケーター ──────────────────────────────────
        mic_y = self._height / 2

        # 青い丸 (グローなしのフラットな青)
        painter.setBrush(QtGui.QColor(84, 164, 255))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QRectF(mic_x - mic_r, mic_y - mic_r, mic_r * 2, mic_r * 2))

        # ── 波形バー ──────────────────────────────────────────────────
        max_bar_h = self._height * 0.45
        center_y = self._height / 2
        self._idle_phase += 0.10
        is_active = np.max(self._amplitudes) > 0.05

        pen = QtGui.QPen()
        pen.setWidthF(bar_w)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setColor(QtGui.QColor(160, 175, 190, 220)) # 波形の色

        for i in range(n_bars):
            x = bar_start_x + i * (bar_w + bar_gap) + bar_w / 2

            if is_active:
                amp = self._amplitudes[i]
                center_bias = 1.0 - abs(i - n_bars / 2) / (n_bars / 2) * 0.15
                amp = min(amp * center_bias * 1.5, 1.0)
                h = max(4, amp * max_bar_h)
            else:
                dist_from_center = abs(i - n_bars / 2 + 0.5) / (n_bars / 2)
                idle_amp = (
                    0.25
                    + 0.15 * np.sin(self._idle_phase * 1.5 + i * 0.4)
                    * np.exp(-dist_from_center * dist_from_center * 2.0)
                )
                h = max(4, idle_amp * max_bar_h * 0.8)

            y1 = center_y - h / 2
            y2 = center_y + h / 2

            painter.setPen(pen)
            painter.drawLine(QtCore.QPointF(x, y1), QtCore.QPointF(x, y2))

        painter.end()
