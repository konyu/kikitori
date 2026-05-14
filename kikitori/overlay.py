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

        # Aqua Voice 風カプセルサイズ（左右マージン30px、コンテンツ110px）
        self._width = 170
        self._height = 44
        self.setFixedSize(self._width, self._height)

        self._center_on_screen()

        # Animation timer (~30fps)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)

        # Waveform data (36 bars for display)
        self._amplitudes = np.zeros(36, dtype=np.float32)
        self._idle_phase = 0.0

    def _center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self._width) // 2
        y = screen.height() - self._height - 28
        self.move(x, y)

    def update_amplitudes(self, amplitudes: np.ndarray):
        """外部から波形データを更新（任意の長さ → 36本にリサンプル）"""
        if len(amplitudes) == 0:
            self._amplitudes.fill(0.0)
        elif len(amplitudes) == 36:
            self._amplitudes = amplitudes.astype(np.float32)
        else:
            old_x = np.linspace(0, 1, len(amplitudes))
            new_x = np.linspace(0, 1, 36)
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
        grad = QtGui.QLinearGradient(0, 0, 0, self._height)
        grad.setColorAt(0.0, QtGui.QColor(50, 55, 70, 165))
        grad.setColorAt(0.5, QtGui.QColor(42, 47, 62, 170))
        grad.setColorAt(1.0, QtGui.QColor(38, 43, 58, 175))
        painter.fillPath(path, grad)

        # ── 中央寄せレイアウト計算 ────────────────────────────────────
        n_bars = 36
        mic_r = 7
        mic_gap = 10
        bar_w = 1.0

        mic_diameter = mic_r * 2
        start_x = 30                              # 左マージン 30px
        mic_x = start_x + mic_r                   # 30 + 7 = 37
        bar_start_x = mic_x + mic_r + mic_gap     # 37 + 7 + 10 = 54
        bar_area_w = self._width - bar_start_x - 30  # 右マージン 30px → 170-54-30 = 86
        bar_gap = (bar_area_w - n_bars * bar_w) / (n_bars - 1)  # (86-36)/35 ≈ 1.43

        # ── 青いマイクインジケーター ──────────────────────────────────
        mic_y = self._height / 2

        # 外側グロー
        glow = QtGui.QRadialGradient(mic_x, mic_y, mic_r + 4)
        glow.setColorAt(0.0, QtGui.QColor(80, 160, 255, 60))
        glow.setColorAt(1.0, QtGui.QColor(80, 160, 255, 0))
        painter.setBrush(glow)
        painter.drawEllipse(
            QtCore.QRectF(mic_x - mic_r - 4, mic_y - mic_r - 4, (mic_r + 4) * 2, (mic_r + 4) * 2)
        )

        # 青い丸
        mic_grad = QtGui.QRadialGradient(mic_x, mic_y - 2, mic_r)
        mic_grad.setColorAt(0.0, QtGui.QColor(120, 185, 255, 255))
        mic_grad.setColorAt(0.6, QtGui.QColor(70, 140, 240, 255))
        mic_grad.setColorAt(1.0, QtGui.QColor(50, 110, 220, 255))
        painter.setBrush(mic_grad)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QRectF(mic_x - mic_r, mic_y - mic_r, mic_r * 2, mic_r * 2))

        # ── 波形バー ──────────────────────────────────────────────────
        max_bar_h = self._height * 0.40
        center_y = self._height / 2
        self._idle_phase += 0.10
        is_active = np.max(self._amplitudes) > 0.05

        for i in range(n_bars):
            x = bar_start_x + i * (bar_w + bar_gap) + bar_w / 2

            if is_active:
                amp = self._amplitudes[i]
                center_bias = 1.0 - abs(i - n_bars / 2) / (n_bars / 2) * 0.15
                amp = min(amp * center_bias * 1.3, 1.0)
                h = max(2, amp * max_bar_h)
                alpha = int(80 + 160 * amp)
            else:
                dist_from_center = abs(i - n_bars / 2 + 0.5) / (n_bars / 2)
                idle_amp = (
                    0.22
                    + 0.18 * np.sin(self._idle_phase * 1.2)
                    * np.exp(-dist_from_center * dist_from_center * 4.0)
                )
                h = max(1.5, idle_amp * max_bar_h * 0.55)
                alpha = int(45 + 35 * idle_amp)

            y1 = center_y - h / 2
            y2 = center_y + h / 2

            bar_grad = QtGui.QLinearGradient(x, y1, x, y2)
            bar_grad.setColorAt(0.0, QtGui.QColor(220, 230, 245, alpha))
            bar_grad.setColorAt(1.0, QtGui.QColor(180, 190, 210, int(alpha * 0.6)))

            pen = QtGui.QPen()
            pen.setWidthF(1.0)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            pen.setBrush(bar_grad)
            painter.setPen(pen)
            painter.drawLine(QtCore.QPointF(x, y1), QtCore.QPointF(x, y2))

        painter.end()
