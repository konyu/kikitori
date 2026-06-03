"""キーワード（専門用語）管理ダイアログ（PySide6）

~/.kikitori_glossary.yaml の用語リストを GUI 上で編集・保存し、
即座に認識プロンプトに反映する。
"""

from pathlib import Path

from PySide6 import QtCore, QtWidgets

from kikitori.glossary import Glossary
from kikitori.theme import apply_dialog_theme


class GlossaryDialog(QtWidgets.QDialog):
    """キーワード管理ダイアログ。

    用語の一覧表示・追加・編集・削除に加え、
    ファイルを外部エディタで開く / 再読み込み が可能。
    保存時に YAML 書き込み → Glossary 再読み込み → 即時反映。

    シグナルを使わず、exec() の戻り値で親に通知する。
    （PySide6 + macOS で QDialog のシグナル接続破棄時にクラッシュする問題を回避）
    """

    # シグナルを使わない（exec() の戻り値 + on_reload コールバックで判断）

    def __init__(self, glossary: Glossary, on_reload=None, parent=None):
        super().__init__(parent)

        self._glossary = glossary
        self._terms: list[str] = list(glossary.get_terms())  # 編集中のコピー
        self._edited = False
        self._on_reload = on_reload

        self.setWindowTitle("キーワード設定")
        self.setMinimumWidth(460)
        self.setMinimumHeight(360)
        # macOS で setWindowFlags 後の destroy でクラッシュする場合があるため
        # WindowContextHelpButtonHint のみ除外する設定は行わない

        apply_dialog_theme(self)
        self._build_ui()
        self._populate_list()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ── ファイルパス + 操作ボタン ──
        file_row = QtWidgets.QHBoxLayout()
        file_row.setSpacing(8)

        path_label = QtWidgets.QLabel(f"ファイル: {self._glossary.path}")
        path_label.setProperty("secondary", "true")
        path_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        file_row.addWidget(path_label)
        file_row.addStretch()

        open_btn = QtWidgets.QPushButton("ファイルを開く")
        open_btn.clicked.connect(self._open_file)
        file_row.addWidget(open_btn)

        reload_btn = QtWidgets.QPushButton("再読み込み")
        reload_btn.clicked.connect(self._reload_from_file)
        file_row.addWidget(reload_btn)

        main_layout.addLayout(file_row)

        # ── 用語リスト + 編集ボタン ──
        list_row = QtWidgets.QHBoxLayout()
        list_row.setSpacing(8)

        self._term_list = QtWidgets.QListWidget()
        self._term_list.setAlternatingRowColors(True)
        self._term_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self._term_list.itemDoubleClicked.connect(self._edit_term)
        self._term_list.currentItemChanged.connect(self._on_selection_changed)
        list_row.addWidget(self._term_list)

        btn_col = QtWidgets.QVBoxLayout()
        btn_col.setSpacing(6)

        self._add_btn = QtWidgets.QPushButton("＋ 追加")
        self._add_btn.clicked.connect(self._add_term)
        btn_col.addWidget(self._add_btn)

        self._edit_btn = QtWidgets.QPushButton("✎ 編集")
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._edit_term)
        btn_col.addWidget(self._edit_btn)

        self._delete_btn = QtWidgets.QPushButton("🗑 削除")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._delete_term)
        btn_col.addWidget(self._delete_btn)

        btn_col.addStretch()

        list_row.addLayout(btn_col)
        main_layout.addLayout(list_row)

        # ── 件数表示 ──
        self._count_label = QtWidgets.QLabel()
        self._count_label.setProperty("secondary", "true")
        main_layout.addWidget(self._count_label)

        # ── ボタン ──
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._save_btn = QtWidgets.QPushButton("保存して適用")
        self._save_btn.setProperty("primary", "true")
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._save_and_apply)
        btn_layout.addWidget(self._save_btn)

        main_layout.addLayout(btn_layout)

        self._update_count()

    # ── リスト操作 ────────────────────────────────────────────────────

    def _populate_list(self):
        """編集中の用語リストを QListWidget に反映する。"""
        self._term_list.clear()
        for term in self._terms:
            self._term_list.addItem(term)

    def _on_selection_changed(self, current, previous):
        has_selection = current is not None
        self._edit_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

    def _add_term(self):
        text, ok = QtWidgets.QInputDialog.getText(
            self, "用語の追加", "追加する用語を入力してください:"
        )
        if ok and text.strip():
            term = text.strip()
            if term not in self._terms:
                self._terms.append(term)
                self._term_list.addItem(term)
                self._term_list.setCurrentRow(self._term_list.count() - 1)
                self._edited = True
                self._update_count()

    def _edit_term(self):
        current_item = self._term_list.currentItem()
        if current_item is None:
            return

        old_idx = self._term_list.currentRow()
        old_text = current_item.text()

        text, ok = QtWidgets.QInputDialog.getText(
            self, "用語の編集", "用語を編集してください:", text=old_text
        )
        if ok and text.strip():
            new_text = text.strip()
            if new_text != old_text and new_text not in self._terms:
                self._terms[old_idx] = new_text
                current_item.setText(new_text)
                self._edited = True
                self._update_count()

    def _delete_term(self):
        current_row = self._term_list.currentRow()
        if current_row < 0:
            return

        term = self._terms[current_row]
        confirm = QtWidgets.QMessageBox.question(
            self,
            "削除の確認",
            f"用語「{term}」を削除しますか？",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        del self._terms[current_row]
        self._term_list.takeItem(current_row)
        self._edited = True
        self._update_count()

    def _update_count(self):
        self._count_label.setText(f"登録件数: {len(self._terms)} 件")
        self._save_btn.setEnabled(self._edited)

    # ── ファイル操作 ──────────────────────────────────────────────────

    def _open_file(self):
        """用語集ファイルを OS 標準エディタで開く。"""
        import subprocess

        path = self._glossary.path
        if not path.exists():
            self._save_terms_to_file(path)

        subprocess.call(["open", str(path)])

    def _reload_from_file(self):
        """用語集ファイルから再読み込みし、リストをリセットする。"""
        if self._edited:
            confirm = QtWidgets.QMessageBox.question(
                self,
                "再読み込みの確認",
                "現在の編集中の内容が失われます。\nファイルから再読み込みしますか？",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        self._glossary.load()
        self._terms = list(self._glossary.get_terms())
        self._edited = False
        self._populate_list()
        self._update_count()

        # 再読み込みが完了したので親に通知（シグナルではなくコールバック）
        if self._on_reload is not None:
            self._on_reload()

    # ── 保存 ──────────────────────────────────────────────────────────

    def _save_terms_to_file(self, path: Path):
        """用語リストを YAML ファイルに書き込む。"""
        import yaml

        try:
            data = {"terms": self._terms}
            path.write_text(
                yaml.dump(
                    data,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, "保存エラー", f"ファイルの保存に失敗しました:\n{e}"
            )
            raise

    def _save_and_apply(self):
        """用語リストを保存し、ダイアログを Accepted で閉じる。

        即時反映は親側で exec() の戻り値を確認して行う。
        """
        try:
            self._save_terms_to_file(self._glossary.path)
        except Exception:
            return  # エラーは _save_terms_to_file 内で表示済み

        self._edited = False
        self._save_btn.setEnabled(False)
        self.accept()
