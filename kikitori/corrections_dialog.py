"""校正辞書管理ダイアログ（PySide6）

~/.kikitori_corrections.yaml の「間違い→訂正」ペアを GUI 上で編集・保存し、
即座に STT 結果の校正に反映する。
"""
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from kikitori.config import DEBUG
from kikitori.corrections import Corrections
from kikitori.i18n import t
from kikitori.theme import apply_dialog_theme


class _EditPairDialog(QtWidgets.QDialog):
    """単一ペアの追加・編集ダイアログ。"""

    def __init__(self, language: str = "ja", wrong: str = "", right: str = "", parent=None):
        super().__init__(parent)
        self._lang = language

        title_key = "corrections.edit_pair.title_edit" if wrong else "corrections.edit_pair.title_add"
        self.setWindowTitle(self._tr(title_key))
        self.setMinimumWidth(360)
        apply_dialog_theme(self)

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._wrong_input = QtWidgets.QLineEdit(wrong)
        self._wrong_input.setPlaceholderText(
            self._tr("corrections.edit_pair.wrong_placeholder")
        )
        layout.addRow(self._tr("corrections.edit_pair.wrong_label"), self._wrong_input)

        self._right_input = QtWidgets.QLineEdit(right)
        self._right_input.setPlaceholderText(
            self._tr("corrections.edit_pair.right_placeholder")
        )
        layout.addRow(self._tr("corrections.edit_pair.right_label"), self._right_input)

        btn_box = QtWidgets.QDialogButtonBox()
        save_btn = btn_box.addButton(
            self._tr("corrections.edit_pair.save_btn"),
            QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
        )
        cancel_btn = btn_box.addButton(
            self._tr("corrections.edit_pair.cancel_btn"),
            QtWidgets.QDialogButtonBox.ButtonRole.RejectRole,
        )
        save_btn.clicked.connect(self._on_accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addRow(btn_box)

    def _tr(self, key: str) -> str:
        return t(key, self._lang)

    def _on_accept(self):
        wrong = self._wrong_input.text().strip()
        if not wrong:
            QtWidgets.QMessageBox.warning(
                self,
                self._tr("corrections.edit_pair.error_title"),
                self._tr("corrections.edit_pair.error_msg"),
            )
            return
        self.accept()

    def get_pair(self) -> tuple[str, str]:
        return self._wrong_input.text().strip(), self._right_input.text().strip()


class CorrectionsDialog(QtWidgets.QDialog):
    """校正辞書管理ダイアログ。

    ペアの一覧表示・追加・編集・削除に加え、
    ファイルを外部エディタで開く / 再読み込み が可能。
    保存時に YAML 書き込み → Corrections 再読み込み → 即時反映。
    """

    def __init__(self, corrections: Corrections, language: str = "ja", parent=None):
        super().__init__(parent)
        self._lang = language

        self._corrections = corrections
        self._items: dict[str, str] = dict(corrections.get_items())
        self._edited = False

        self.setWindowTitle(self._tr("corrections.title"))
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)

        apply_dialog_theme(self)
        self._build_ui()
        self._populate_table()

    def _tr(self, key: str) -> str:
        return t(key, self._lang)

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ファイルパス行
        file_row = QtWidgets.QHBoxLayout()
        file_row.setSpacing(8)

        path_label = QtWidgets.QLabel(
            f"{self._tr('corrections.file_label')} {self._corrections.path}"
        )
        path_label.setProperty("secondary", "true")
        path_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        file_row.addWidget(path_label)
        file_row.addStretch()

        open_btn = QtWidgets.QPushButton(self._tr("corrections.open_file_btn"))
        open_btn.clicked.connect(self._open_file)
        file_row.addWidget(open_btn)

        reload_btn = QtWidgets.QPushButton(self._tr("corrections.reload_btn"))
        reload_btn.clicked.connect(self._reload_from_file)
        file_row.addWidget(reload_btn)

        main_layout.addLayout(file_row)

        # テーブル
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels([
            self._tr("corrections.table.wrong_header"),
            self._tr("corrections.table.right_header"),
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._edit_pair)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        main_layout.addWidget(self._table)

        # ボタン行
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self._add_btn = QtWidgets.QPushButton(self._tr("corrections.add_btn"))
        self._add_btn.clicked.connect(self._add_pair)
        btn_row.addWidget(self._add_btn)

        self._edit_btn = QtWidgets.QPushButton(self._tr("corrections.edit_btn"))
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._edit_pair)
        btn_row.addWidget(self._edit_btn)

        self._delete_btn = QtWidgets.QPushButton(self._tr("corrections.delete_btn"))
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._delete_pair)
        btn_row.addWidget(self._delete_btn)

        main_layout.addLayout(btn_row)

        # カウントラベル
        self._count_label = QtWidgets.QLabel(
            self._tr("corrections.count_label").format(count=0)
        )
        self._count_label.setProperty("secondary", "true")
        main_layout.addWidget(self._count_label)

        # ダイアログボタン
        dialog_btns = QtWidgets.QDialogButtonBox()
        save_btn = dialog_btns.addButton(
            self._tr("corrections.save_btn"),
            QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
        )
        cancel_btn = dialog_btns.addButton(
            self._tr("corrections.cancel_btn"),
            QtWidgets.QDialogButtonBox.ButtonRole.RejectRole,
        )
        save_btn.clicked.connect(self._save_and_apply)
        cancel_btn.clicked.connect(self.reject)
        main_layout.addWidget(dialog_btns)

    def _populate_table(self):
        self._table.setRowCount(len(self._items))
        for row, (wrong, right) in enumerate(self._items.items()):
            wrong_item = QtWidgets.QTableWidgetItem(wrong)
            wrong_item.setFlags(wrong_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, wrong_item)

            right_item = QtWidgets.QTableWidgetItem(right)
            right_item.setFlags(right_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, right_item)

        self._update_count()

    def _on_selection_changed(self):
        has_selection = self._table.currentRow() >= 0
        self._edit_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

    def _add_pair(self):
        dlg = _EditPairDialog(language=self._lang, parent=self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            wrong, right = dlg.get_pair()
            if wrong in self._items:
                ret = QtWidgets.QMessageBox.question(
                    self,
                    self._tr("corrections.overwrite_confirm_title"),
                    self._tr("corrections.overwrite_confirm_msg").format(wrong=wrong),
                )
                if ret != QtWidgets.QMessageBox.StandardButton.Yes:
                    return
            self._items[wrong] = right
            self._edited = True
            self._populate_table()

    def _edit_pair(self):
        row = self._table.currentRow()
        if row < 0:
            return
        old_wrong = self._table.item(row, 0).text()
        old_right = self._table.item(row, 1).text()

        dlg = _EditPairDialog(language=self._lang, wrong=old_wrong, right=old_right, parent=self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            wrong, right = dlg.get_pair()
            if wrong != old_wrong:
                del self._items[old_wrong]
            self._items[wrong] = right
            self._edited = True
            self._populate_table()

    def _delete_pair(self):
        row = self._table.currentRow()
        if row < 0:
            return
        wrong = self._table.item(row, 0).text()
        ret = QtWidgets.QMessageBox.question(
            self,
            self._tr("corrections.delete_confirm_title"),
            self._tr("corrections.delete_confirm_msg").format(wrong=wrong),
        )
        if ret == QtWidgets.QMessageBox.StandardButton.Yes:
            del self._items[wrong]
            self._edited = True
            self._populate_table()

    def _update_count(self):
        self._count_label.setText(
            self._tr("corrections.count_label").format(count=len(self._items))
        )

    def _open_file(self):
        path = self._corrections.path
        if not path.exists():
            try:
                path.write_text(Corrections.generate_template(), encoding="utf-8")
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    self._tr("corrections.error_title"),
                    self._tr("corrections.file_create_error").format(error=e),
                )
                return
        import subprocess
        subprocess.run(["open", "-t", str(path)])

    def _reload_from_file(self):
        self._corrections.load()
        self._items = dict(self._corrections.get_items())
        self._populate_table()
        if self._on_reload:
            self._on_reload()

    def _save_and_apply(self):
        import sys, traceback
        try:
            if DEBUG:
                print("[DEBUG] _save_and_apply: calling save_items", flush=True, file=sys.stderr)
            self._corrections.save_items(self._items)
            if DEBUG:
                print("[DEBUG] _save_and_apply: save_items OK", flush=True, file=sys.stderr)
            if DEBUG:
                print("[DEBUG] _save_and_apply: calling accept", flush=True, file=sys.stderr)
            self.accept()
            if DEBUG:
                print("[DEBUG] _save_and_apply: accept OK", flush=True, file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] _save_and_apply failed: {e}", flush=True, file=sys.stderr)
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self,
                self._tr("corrections.error_title"),
                self._tr("corrections.save_error").format(error=e),
            )
