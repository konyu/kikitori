"""設定編集ダイアログ（PySide6）

言語、UI表示言語、ホットキー、最低録音時間、無音判定閾値を
GUI 上で編集・保存し、即時反映する。
"""

from PySide6 import QtCore, QtWidgets

from kikitori.config import (
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    MIN_DURATION_MS,
    SILENCE_RMS_THRESHOLD,
)
from kikitori.i18n import t, get_language_labels, get_ui_language_labels
from kikitori.settings import detect_os_language
from kikitori.theme import apply_dialog_theme


class HotkeyEditor(QtWidgets.QWidget):
    """ホットキー設定用の複合ウィジェット。

    修飾キー（Cmd/Option/Ctrl/Shift）のチェックボックスと
    追加キーのテキスト入力で構成する。
    """

    hotkey_changed = QtCore.Signal()

    MODIFIER_MAP: dict[str, str] = {
        "cmd": "Cmd (\u2318)",
        "option": "Option (\u2325)",
        "ctrl": "Ctrl (\u2303)",
        "shift": "Shift (\u21e7)",
    }

    def __init__(self, language: str = "ja", parent=None):
        super().__init__(parent)
        self._lang = language

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

        self._extra_key_label = QtWidgets.QLabel(t("settings.hotkey_extra_key", language))
        row2.addWidget(self._extra_key_label)

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

    def __init__(self, current_settings: dict, language: str = "ja", parent=None):
        super().__init__(parent)
        self._lang = language

        self.setWindowTitle(t("settings.title", language))
        self.setMinimumWidth(520)
        # macOS で setWindowFlags 後の destroy でクラッシュする場合があるため
        # WindowContextHelpButtonHint のみ除外する設定は行わない

        self._current = current_settings.copy()

        # 言語ラベルマップ {code: label} → {label: code}
        self._languages = {label: code for code, label in get_language_labels().items()}
        self._ui_languages = {label: code for code, label in get_ui_language_labels().items()}

        apply_dialog_theme(self)
        self._build_ui()
        self._load_values()

    def _tr(self, key: str) -> str:
        """現在の UI 言語で翻訳文字列を取得する。"""
        return t(key, self._lang)

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

        # ── 言語（音声認識） ──
        self._lang_combo = QtWidgets.QComboBox()
        self._lang_combo.setEditable(False)
        for display, code in self._languages.items():
            self._lang_combo.addItem(f"{display} ({code})", code)
        form_layout.addRow(self._tr("settings.lang_label"), self._lang_combo)

        # ── UI 表示言語 ──
        self._ui_lang_combo = QtWidgets.QComboBox()
        self._ui_lang_combo.setEditable(False)
        for display, code in self._ui_languages.items():
            self._ui_lang_combo.addItem(display, code)
        form_layout.addRow(self._tr("settings.ui_lang_label"), self._ui_lang_combo)

        # ── ホットキー ──
        self._hotkey_editor = HotkeyEditor(language=self._lang)
        form_layout.addRow(self._tr("settings.hotkey_label"), self._hotkey_editor)

        # ── 最低録音時間 ──
        dur_layout = QtWidgets.QHBoxLayout()
        self._min_dur_spin = QtWidgets.QSpinBox()
        self._min_dur_spin.setRange(100, 5000)
        self._min_dur_spin.setSingleStep(100)
        self._min_dur_spin.setSuffix(" ms")
        dur_layout.addWidget(self._min_dur_spin)

        dur_hint = QtWidgets.QLabel(self._tr("settings.min_dur_hint"))
        dur_hint.setProperty("secondary", "true")
        dur_layout.addWidget(dur_hint)
        dur_layout.addStretch()
        form_layout.addRow(self._tr("settings.min_dur_label"), dur_layout)

        # ── 無音判定閾値 ──
        silence_layout = QtWidgets.QHBoxLayout()
        self._silence_spin = QtWidgets.QSpinBox()
        self._silence_spin.setRange(1, 50000)
        self._silence_spin.setSingleStep(100)
        self._silence_spin.setSuffix(" /10000")
        silence_layout.addWidget(self._silence_spin)

        silence_hint = QtWidgets.QLabel(self._tr("settings.silence_hint"))
        silence_hint.setProperty("secondary", "true")
        silence_layout.addWidget(silence_hint)
        silence_layout.addStretch()
        form_layout.addRow(self._tr("settings.silence_label"), silence_layout)

        main_layout.addWidget(form)

        # ── ボタン ──
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)

        reset_btn = QtWidgets.QPushButton(self._tr("settings.reset_btn"))
        reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton(self._tr("settings.cancel_btn"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QtWidgets.QPushButton(self._tr("settings.save_btn"))
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

        ui_lang = self._current.get("ui_language") or detect_os_language()
        idx = self._ui_lang_combo.findData(ui_lang)
        if idx >= 0:
            self._ui_lang_combo.setCurrentIndex(idx)

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
            "ui_language": self._ui_lang_combo.currentData() or "en",
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
