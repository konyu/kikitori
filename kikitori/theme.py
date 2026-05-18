"""macOS システムテーマ検出とダイアログ用スタイルシート。

PySide6 の QStyleHints.colorScheme() を使用して
ダーク/ライトモードを検出し、対応するスタイルシートを提供する。
"""

from PySide6 import QtCore, QtWidgets


# ── macOS System Settings 風カラーパレット（ダーク）────────────────────────
_DARK = {
    "window_bg": "#1c1c1e",
    "card_bg": "#2c2c2e",
    "input_bg": "#3a3a3c",
    "input_border": "#48484a",
    "text_primary": "#ffffff",
    "text_secondary": "#98989d",
    "accent": "#0a84ff",          # macOS ダークモード アクセント
    "accent_hover": "#0071e3",
    "danger": "#ff453a",
    "separator": "#38383a",
    "btn_secondary_bg": "#3a3a3c",
    "btn_secondary_border": "#48484a",
    "scroll_bg": "#2c2c2e",
    "scroll_handle": "#636366",
    "placeholder": "#8e8e93",
}

# ── macOS System Settings 風カラーパレット（ライト）────────────────────────
_LIGHT = {
    "window_bg": "#f5f5f7",
    "card_bg": "#ffffff",
    "input_bg": "#ffffff",
    "input_border": "#d1d1d6",
    "text_primary": "#1d1d1f",
    "text_secondary": "#6e6e73",
    "accent": "#007aff",
    "accent_hover": "#0066d4",
    "danger": "#ff3b30",
    "separator": "#d1d1d6",
    "btn_secondary_bg": "#ffffff",
    "btn_secondary_border": "#d1d1d6",
    "scroll_bg": "#f5f5f7",
    "scroll_handle": "#c7c7cc",
    "placeholder": "#8e8e93",
}


def is_dark_mode() -> bool:
    """システムがダークモードかどうかを検出する。

    PySide6 の QStyleHints.colorScheme() を優先使用し、
    失敗した場合は macOS NSAppearance 経由のフォールバックを試行する。
    """
    try:
        scheme = QtWidgets.QApplication.styleHints().colorScheme()
        return scheme == QtCore.Qt.ColorScheme.Dark
    except Exception:
        pass

    # macOS フォールバック
    try:
        from AppKit import NSAppearance
        appearance = NSAppearance.currentAppearance()
        name = appearance.name() if hasattr(appearance, "name") else str(appearance)
        return "Dark" in name
    except Exception:
        pass

    return False


def _build_stylesheet(p: dict) -> str:
    """カラーパレット辞書から Qt スタイルシート文字列を生成する。"""
    return f"""
        /* ── ダイアログ全体 ── */
        QDialog {{
            background-color: {p["window_bg"]};
            color: {p["text_primary"]};
        }}

        /* ── ラベル ── */
        QLabel {{
            color: {p["text_primary"]};
            background-color: transparent;
        }}

        /* ── グループボックス ── */
        QGroupBox {{
            color: {p["text_primary"]};
            background-color: transparent;
            border: 1px solid {p["separator"]};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 8px;
            padding-left: 12px;
            padding-right: 12px;
            padding-bottom: 12px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {p["text_secondary"]};
            font-size: 11px;
        }}

        /* ── 入力欄 ── */
        QLineEdit, QTextEdit, QComboBox {{
            background-color: {p["input_bg"]};
            color: {p["text_primary"]};
            border: 1px solid {p["input_border"]};
            border-radius: 6px;
            padding: 6px 10px;
            selection-background-color: {p["accent"]};
            selection-color: #ffffff;
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 1.5px solid {p["accent"]};
        }}
        QLineEdit::placeholder, QTextEdit::placeholder {{
            color: {p["placeholder"]};
        }}

        /* ── コンボボックス ── */
        QComboBox {{
            padding: 4px 10px;
            min-height: 22px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {p["card_bg"]};
            color: {p["text_primary"]};
            border: 1px solid {p["separator"]};
            border-radius: 6px;
            selection-background-color: {p["accent"]};
            outline: none;
        }}

        /* ── スピンボックス ── */
        QSpinBox {{
            background-color: {p["input_bg"]};
            color: {p["text_primary"]};
            border: 1px solid {p["input_border"]};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        QSpinBox:focus {{
            border: 1.5px solid {p["accent"]};
        }}

        /* ── チェックボックス ── */
        QCheckBox {{
            color: {p["text_primary"]};
            spacing: 4px;
        }}

        /* ── プライマリボタン ── */
        QPushButton[primary="true"] {{
            background-color: {p["accent"]};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: 500;
        }}
        QPushButton[primary="true"]:hover {{
            background-color: {p["accent_hover"]};
        }}
        QPushButton[primary="true"]:pressed {{
            background-color: {p["accent"]};
        }}
        QPushButton[primary="true"]:disabled {{
            background-color: {p["separator"]};
            color: {p["text_secondary"]};
        }}

        /* ── セカンダリボタン ── */
        QPushButton {{
            background-color: {p["btn_secondary_bg"]};
            color: {p["text_primary"]};
            border: 1px solid {p["btn_secondary_border"]};
            border-radius: 6px;
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: {p["separator"]};
        }}
        QPushButton:pressed {{
            background-color: {p["btn_secondary_bg"]};
        }}
        QPushButton:disabled {{
            background-color: transparent;
            color: {p["text_secondary"]};
            border-color: {p["separator"]};
        }}

        /* ── セカンダリテキストラベル ── */
        QLabel[secondary="true"] {{
            color: {p["text_secondary"]};
            background-color: transparent;
        }}

        /* ── リストウィジェット ── */
        QListWidget {{
            background-color: {p["input_bg"]};
            color: {p["text_primary"]};
            border: 1px solid {p["input_border"]};
            border-radius: 6px;
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{
            border-radius: 4px;
            padding: 6px 8px;
        }}
        QListWidget::item:selected {{
            background-color: {p["accent"]};
            color: #ffffff;
        }}
        QListWidget::item:hover:!selected {{
            background-color: {p["separator"]};
        }}

        /* ── メニュー ── */
        QMenu {{
            background-color: {p["card_bg"]};
            color: {p["text_primary"]};
            border: 1px solid {p["separator"]};
            border-radius: 6px;
            padding: 6px;
        }}
        QMenu::item:selected {{
            background-color: {p["accent"]};
            color: #ffffff;
            border-radius: 4px;
        }}

        /* ── スクロールバー ── */
        QScrollBar:vertical {{
            background: {p["scroll_bg"]};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {p["scroll_handle"]};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {p["text_secondary"]};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """


def dialog_stylesheet() -> str:
    """現在のシステムテーマに対応したダイアログ用スタイルシートを返す。"""
    palette = _DARK if is_dark_mode() else _LIGHT
    return _build_stylesheet(palette)


def apply_dialog_theme(widget: QtWidgets.QWidget) -> None:
    """指定ウィジェット（ダイアログ等）にテーマ対応のスタイルシートを適用する。"""
    widget.setStyleSheet(dialog_stylesheet())
