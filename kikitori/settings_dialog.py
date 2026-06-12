"""設定編集ダイアログ（PySide6）

言語、プロンプト、ホットキー、最低録音時間、モデル名を
GUI 上で編集・保存し、即時反映する。
"""

from PySide6 import QtCore, QtWidgets

from kikitori.config import (
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    MIN_DURATION_MS,
    SILENCE_RMS_THRESHOLD,
)
from kikitori.theme import apply_dialog_theme

# Whisper がサポートする主要言語コード（表示名 → コード）
_LANGUAGES: dict[str, str] = {
    "日本語": "ja",
    "English": "en",
    "中文（简体）": "zh",
    "中文（繁體）": "zh",
    "한국어": "ko",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "Español": "es",
    "Português": "pt",
    "Русский": "ru",
    "Nederlands": "nl",
    "Polski": "pl",
    "Türkçe": "tr",
    "Arabic": "ar",
    "Hindi": "hi",
    "Thai": "th",
    "Tiếng Việt": "vi",
}


class HotkeyEditor(QtWidgets.QWidget):
    """ホットキー設定用の複合ウィジェット。

    修飾キー（Cmd/Option/Ctrl/Shift）のチェックボックスと
    追加キーのテキスト入力で構成する。
    """

    hotkey_changed = QtCore.Signal()

    MODIFIER_MAP: dict[str, str] = {
        "cmd": "Cmd (⌘)",
        "option": "Option (⌥)",
        "ctrl": "Ctrl (⌃)",
        "shift": "Shift (⇧)",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 行1: 修飾キーチェックボックス
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(24)

        self._checkboxes: dict[str, QtWidgets.QCheckBox] = {}
        for key, label in self.MODIFIER_MAP.items():
            cb = QtWidgets.QCheckBox(label)
            cb.toggled.connect(lambda checked: self.hotkey_changed.emit())
            row1.addWidget(cb)
            self._checkboxes[key] = cb
        row1.addStretch()

        # 行2: 追加キー
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(8)

        row2.addWidget(QtWidgets.QLabel("+ キー:"))

        self._extra_key = QtWidgets.QLineEdit()
        self._extra_key.setPlaceholderText("F13, a, 1...")
        self._extra_key.setMinimumWidth(120)
        self._extra_key.textChanged.connect(lambda text: self.hotkey_changed.emit())
        row2.addWidget(self._extra_key)

        row2.addStretch()

        layout.addLayout(row1)
        layout.addLayout(row2)

    def set_hotkey(self, names: list[str]):
        """ホットキー名のリストからウィジェットの状態を復元する。"""
        # 全チェックボックスをオフ
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

        self._extra_key.blockSignals(True)
        self._extra_key.clear()
        self._extra_key.blockSignals(False)

        extra = ""
        for name in names:
            name_lower = name.lower().strip()
            if name_lower in self._checkboxes:
                self._checkboxes[name_lower].blockSignals(True)
                self._checkboxes[name_lower].setChecked(True)
                self._checkboxes[name_lower].blockSignals(False)
            else:
                extra = name

        self._extra_key.blockSignals(True)
        self._extra_key.setText(extra)
        self._extra_key.blockSignals(False)

    def get_hotkey(self) -> list[str]:
        """現在のウィジェット状態からホットキー名のリストを生成する。"""
        names: list[str] = []
        for key, cb in self._checkboxes.items():
            if cb.isChecked():
                names.append(key)

        extra = self._extra_key.text().strip()
        if extra:
            names.append(extra)

        if not names:
            return ["option"]  # デフォルト

        return names




class SettingsDialog(QtWidgets.QDialog):
    """設定編集ダイアログ。

    編集内容を保存すると、即座に ~/.kikitori_settings.yaml に書き込む。
    親は exec() の戻り値で Accepted/Rejected を判断する。
    """

    # シグナルを使わない（exec() の戻り値で判断）
    # PySide6 + macOS で QDialog のシグナル接続破棄時にクラッシュする問題を回避

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Kikitori 設定")
        self.setMinimumWidth(520)
        # macOS で setWindowFlags 後の destroy でクラッシュする場合があるため
        # WindowContextHelpButtonHint のみ除外する設定は行わない

        self._current = current_settings.copy()

        apply_dialog_theme(self)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        form = QtWidgets.QWidget()
        form_layout = QtWidgets.QFormLayout(form)
        form_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(12)
        form_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        # ── 言語 ──
        self._lang_combo = QtWidgets.QComboBox()
        self._lang_combo.setEditable(False)
        for display, code in _LANGUAGES.items():
            self._lang_combo.addItem(f"{display} ({code})", code)
        form_layout.addRow("言語:", self._lang_combo)

        # ── ホットキー ──
        self._hotkey_editor = HotkeyEditor()
        form_layout.addRow("ホットキー:", self._hotkey_editor)

        # ── 最低録音時間 ──
        dur_layout = QtWidgets.QHBoxLayout()
        self._min_dur_spin = QtWidgets.QSpinBox()
        self._min_dur_spin.setRange(100, 5000)
        self._min_dur_spin.setSingleStep(100)
        self._min_dur_spin.setSuffix(" ms")
        dur_layout.addWidget(self._min_dur_spin)

        dur_hint = QtWidgets.QLabel(
            "（これより短い録音は誤動作として無視されます）"
        )
        dur_hint.setProperty("secondary", "true")
        dur_layout.addWidget(dur_hint)
        dur_layout.addStretch()
        form_layout.addRow("最低録音時間:", dur_layout)

        # ── 無音判定閾値 ──
        silence_layout = QtWidgets.QHBoxLayout()
        self._silence_spin = QtWidgets.QSpinBox()
        self._silence_spin.setRange(1, 50000)
        self._silence_spin.setSingleStep(100)
        self._silence_spin.setSuffix(" /10000")
        silence_layout.addWidget(self._silence_spin)

        silence_hint = QtWidgets.QLabel(
            "（100=0.01、これ以下は無音として無視）"
        )
        silence_hint.setProperty("secondary", "true")
        silence_layout.addWidget(silence_hint)
        silence_layout.addStretch()
        form_layout.addRow("無音判定閾値:", silence_layout)

        main_layout.addWidget(form)

        # ── ボタン ──
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)

        reset_btn = QtWidgets.QPushButton("デフォルトに戻す")
        reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QtWidgets.QPushButton("保存して適用")
        save_btn.setProperty("primary", "true")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_apply)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

    def _load_values(self):
        """現在の設定値をウィジェットに反映する。"""
        lang_code = self._current.get("language", DEFAULT_LANGUAGE)
        idx = self._lang_combo.findData(lang_code)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        else:
            self._lang_combo.setEditText(lang_code)

        hotkey = self._current.get("hotkey", DEFAULT_HOTKEY)
        self._hotkey_editor.set_hotkey(hotkey)

        min_dur = self._current.get("min_duration_ms", MIN_DURATION_MS)
        self._min_dur_spin.setValue(int(min_dur))

        silence = self._current.get("silence_rms_threshold", SILENCE_RMS_THRESHOLD)
        self._silence_spin.setValue(int(float(silence) * 10000))

    def _collect_values(self) -> dict:
        """ウィジェットから設定辞書を生成する。"""
        lang_code = self._lang_combo.currentData()
        if lang_code is None:
            lang_code = self._lang_combo.currentText().strip()

        return {
            "language": lang_code,
            "hotkey": self._hotkey_editor.get_hotkey(),
            "min_duration_ms": self._min_dur_spin.value(),
            "silence_rms_threshold": self._silence_spin.value() / 10000,
        }

    @property
    def reset_requested(self) -> bool:
        """デフォルトに戻すが押されたかどうか。"""
        return getattr(self, "_reset_requested", False)

    def _save_and_apply(self):
        """ダイアログを Accepted で閉じる。親は exec() の戻り値で判断する。"""
        self.accept()

    def _reset_to_defaults(self):
        """設定をデフォルトに戻してダイアログを閉じる。"""
        from kikitori.settings import reset_settings
        reset_settings()
        self._reset_requested = True
        self.accept()
