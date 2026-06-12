"""多言語化文字列辞書。

キーで参照し、言語コードで ja/en を切り替える。
未定義キー・言語は ja にフォールバックする。
"""

# fmt: off
STRINGS: dict[str, dict[str, str]] = {
    "ja": {
        # ── ui_pyside（メニューバー・ステータス・ログ） ──
        "app.tooltip": "Kikitori",
        "app.status.idle": "○ 待機中",
        "app.status.recording": "🔴 録音中...",
        "app.status.error": "❌ 音声認識の初期化失敗",
        "app.menu.record_start": "🔴 録音開始",
        "app.menu.record_stop": "⏹ 録音停止",
        "app.menu.settings": "⚙️ 設定",
        "app.menu.glossary": "📚 用語集",
        "app.menu.corrections": "📝 校正辞書",
        "app.menu.quit": "終了",
        "app.log.model_ready": "音声認識の準備完了",
        "app.log.model_failed": "音声認識の初期化に失敗しました",
        "app.log.settings_updated": "設定を更新しました",
        "app.log.glossary_reloaded": "キーワードを再読み込みしました",
        "app.log.corrections_reloaded": "校正辞書を再読み込みしました",
        "app.log.settings_file_changed": "設定ファイル変更を反映しました",
        "app.log.corrections_loaded": "校正辞書を読み込みました（{count} 件）",
        "app.log.listener_start": "ホットキーリスナーを開始します。Ctrl+C で終了。",
        "app.log.empty_audio": "録音データが空です",
        "app.log.too_short": "録音が短すぎます（{duration_ms:.0f}ms < {min_ms:.0f}ms）— 認識しません",
        "app.log.silence": "無音と判定されました（RMS={rms:.4f} < {threshold}）— 認識しません",
        "app.log.record_failed": "録音開始失敗: {error}",
        "app.banner.title": "Kikitori",
        "app.banner.hotkey": "ホットキー: {hotkey} (押下中録音 / 解放で出力)",

        # ── settings_dialog ──
        "settings.title": "Kikitori 設定",
        "settings.lang_label": "認識言語:",
        "settings.ui_lang_label": "UI 表示言語:",
        "settings.hotkey_label": "ホットキー:",
        "settings.hotkey_extra_key": "+ キー:",
        "settings.min_dur_label": "最低録音時間:",
        "settings.min_dur_hint": "（これより短い録音は誤動作として無視されます）",
        "settings.silence_label": "無音判定閾値:",
        "settings.silence_hint": "（100=0.01、これ以下は無音として無視）",
        "settings.reset_btn": "デフォルトに戻す",
        "settings.cancel_btn": "キャンセル",
        "settings.save_btn": "保存して適用",

        # ── glossary_dialog ──
        "glossary.title": "キーワード設定",
        "glossary.file_label": "ファイル:",
        "glossary.open_file_btn": "ファイルを開く",
        "glossary.reload_btn": "再読み込み",
        "glossary.add_btn": "＋ 追加",
        "glossary.edit_btn": "✎ 編集",
        "glossary.delete_btn": "🗑 削除",
        "glossary.save_btn": "保存して適用",
        "glossary.cancel_btn": "キャンセル",
        "glossary.add_title": "用語の追加",
        "glossary.add_prompt": "追加する用語を入力してください:",
        "glossary.edit_title": "用語の編集",
        "glossary.edit_prompt": "用語を編集してください:",
        "glossary.delete_confirm_title": "削除の確認",
        "glossary.delete_confirm_msg": "用語「{term}」を削除しますか？",
        "glossary.count_label": "登録件数: {count} 件",
        "glossary.reload_confirm_title": "再読み込みの確認",
        "glossary.reload_confirm_msg": "現在の編集中の内容が失われます。\nファイルから再読み込みしますか？",
        "glossary.save_error_title": "保存エラー",
        "glossary.save_error_msg": "ファイルの保存に失敗しました:\n{error}",

        # ── corrections_dialog ──
        "corrections.title": "校正辞書設定",
        "corrections.file_label": "ファイル:",
        "corrections.open_file_btn": "ファイルを開く",
        "corrections.reload_btn": "再読み込み",
        "corrections.add_btn": "＋ 追加",
        "corrections.edit_btn": "✎ 編集",
        "corrections.delete_btn": "🗑 削除",
        "corrections.save_btn": "保存して適用",
        "corrections.cancel_btn": "キャンセル",
        "corrections.edit_pair.title_add": "校正ペアを追加",
        "corrections.edit_pair.title_edit": "校正ペアを編集",
        "corrections.edit_pair.wrong_label": "間違い:",
        "corrections.edit_pair.right_label": "訂正:",
        "corrections.edit_pair.wrong_placeholder": "例: use effect",
        "corrections.edit_pair.right_placeholder": "例: useEffect",
        "corrections.edit_pair.save_btn": "保存",
        "corrections.edit_pair.cancel_btn": "キャンセル",
        "corrections.edit_pair.error_title": "入力エラー",
        "corrections.edit_pair.error_msg": "間違いの文字列を入力してください。",
        "corrections.table.wrong_header": "間違い",
        "corrections.table.right_header": "訂正",
        "corrections.delete_confirm_title": "削除確認",
        "corrections.delete_confirm_msg": "「{wrong}」を削除しますか？",
        "corrections.count_label": "登録数: {count}",
        "corrections.overwrite_confirm_title": "上書き確認",
        "corrections.overwrite_confirm_msg": "「{wrong}」は既に登録されています。上書きしますか？",
        "corrections.error_title": "エラー",
        "corrections.file_create_error": "ファイルの作成に失敗しました:\n{error}",
        "corrections.save_error": "保存に失敗しました:\n{error}",
        "corrections.reload_confirm_title": "再読み込みの確認",
        "corrections.reload_confirm_msg": "現在の編集中の内容が失われます。\nファイルから再読み込みしますか？",
        "corrections.save_error_title": "保存エラー",
        "corrections.save_error_msg": "ファイルの保存に失敗しました:\n{error}",
    },
    "en": {
        # ── ui_pyside（メニューバー・ステータス・ログ） ──
        "app.tooltip": "Kikitori",
        "app.status.idle": "○ Idle",
        "app.status.recording": "🔴 Recording...",
        "app.status.error": "❌ Model init failed",
        "app.menu.record_start": "🔴 Start Recording",
        "app.menu.record_stop": "⏹ Stop Recording",
        "app.menu.settings": "⚙️ Settings",
        "app.menu.glossary": "📚 Glossary",
        "app.menu.corrections": "📝 Corrections",
        "app.menu.quit": "Quit",
        "app.log.model_ready": "Model ready",
        "app.log.model_failed": "Model init failed",
        "app.log.settings_updated": "Settings updated",
        "app.log.glossary_reloaded": "Glossary reloaded",
        "app.log.corrections_reloaded": "Corrections reloaded",
        "app.log.settings_file_changed": "Settings file changes applied",
        "app.log.corrections_loaded": "Corrections loaded ({count} items)",
        "app.log.listener_start": "Hotkey listener started. Press Ctrl+C to quit.",
        "app.log.empty_audio": "Recording data is empty",
        "app.log.too_short": "Recording too short ({duration_ms:.0f}ms < {min_ms:.0f}ms) — skipped",
        "app.log.silence": "Detected as silence (RMS={rms:.4f} < {threshold}) — skipped",
        "app.log.record_failed": "Recording start failed: {error}",
        "app.banner.title": "Kikitori",
        "app.banner.hotkey": "Hotkey: {hotkey} (hold to record / release to output)",

        # ── settings_dialog ──
        "settings.title": "Kikitori Settings",
        "settings.lang_label": "Recognition language:",
        "settings.ui_lang_label": "UI language:",
        "settings.hotkey_label": "Hotkey:",
        "settings.hotkey_extra_key": "+ Key:",
        "settings.min_dur_label": "Min duration:",
        "settings.min_dur_hint": "(Shorter recordings are ignored as false triggers)",
        "settings.silence_label": "Silence threshold:",
        "settings.silence_hint": "(100=0.01, below is treated as silence)",
        "settings.reset_btn": "Reset to Defaults",
        "settings.cancel_btn": "Cancel",
        "settings.save_btn": "Save & Apply",

        # ── glossary_dialog ──
        "glossary.title": "Glossary",
        "glossary.file_label": "File:",
        "glossary.open_file_btn": "Open File",
        "glossary.reload_btn": "Reload",
        "glossary.add_btn": "＋ Add",
        "glossary.edit_btn": "✎ Edit",
        "glossary.delete_btn": "🗑 Delete",
        "glossary.save_btn": "Save & Apply",
        "glossary.cancel_btn": "Cancel",
        "glossary.add_title": "Add Term",
        "glossary.add_prompt": "Enter a term to add:",
        "glossary.edit_title": "Edit Term",
        "glossary.edit_prompt": "Edit the term:",
        "glossary.delete_confirm_title": "Confirm Delete",
        "glossary.delete_confirm_msg": "Delete term \"{term}\"?",
        "glossary.count_label": "Terms: {count}",
        "glossary.reload_confirm_title": "Confirm Reload",
        "glossary.reload_confirm_msg": "Unsaved changes will be lost.\nReload from file?",
        "glossary.save_error_title": "Save Error",
        "glossary.save_error_msg": "Failed to save file:\n{error}",

        # ── corrections_dialog ──
        "corrections.title": "Corrections",
        "corrections.file_label": "File:",
        "corrections.open_file_btn": "Open File",
        "corrections.reload_btn": "Reload",
        "corrections.add_btn": "＋ Add",
        "corrections.edit_btn": "✎ Edit",
        "corrections.delete_btn": "🗑 Delete",
        "corrections.save_btn": "Save & Apply",
        "corrections.cancel_btn": "Cancel",
        "corrections.edit_pair.title_add": "Add Correction Pair",
        "corrections.edit_pair.title_edit": "Edit Correction Pair",
        "corrections.edit_pair.wrong_label": "Wrong:",
        "corrections.edit_pair.right_label": "Correction:",
        "corrections.edit_pair.wrong_placeholder": "e.g. use effect",
        "corrections.edit_pair.right_placeholder": "e.g. useEffect",
        "corrections.edit_pair.save_btn": "Save",
        "corrections.edit_pair.cancel_btn": "Cancel",
        "corrections.edit_pair.error_title": "Input Error",
        "corrections.edit_pair.error_msg": "Please enter the wrong string.",
        "corrections.table.wrong_header": "Wrong",
        "corrections.table.right_header": "Correction",
        "corrections.delete_confirm_title": "Confirm Delete",
        "corrections.delete_confirm_msg": "Delete \"{wrong}\"?",
        "corrections.count_label": "Items: {count}",
        "corrections.overwrite_confirm_title": "Overwrite Confirm",
        "corrections.overwrite_confirm_msg": "\"{wrong}\" already exists. Overwrite?",
        "corrections.error_title": "Error",
        "corrections.file_create_error": "Failed to create file:\n{error}",
        "corrections.save_error": "Failed to save:\n{error}",
        "corrections.reload_confirm_title": "Confirm Reload",
        "corrections.reload_confirm_msg": "Unsaved changes will be lost.\nReload from file?",
        "corrections.save_error_title": "Save Error",
        "corrections.save_error_msg": "Failed to save file:\n{error}",
    },
}
# fmt: on

# _LANGUAGES / _UI_LANGUAGES は設定ダイアログで使う表示名。
# これらは各言語の自称のため翻訳不要。
_LANGUAGES_LABELS: dict[str, str] = {
    "ja": "日本語",
    "en": "English",
    "zh": "中文（简体）",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "es": "Español",
    "pt": "Português",
    "ru": "Русский",
    "nl": "Nederlands",
    "pl": "Polski",
    "tr": "Türkçe",
    "ar": "Arabic",
    "hi": "Hindi",
    "th": "Thai",
    "vi": "Tiếng Việt",
}

_UI_LANGUAGES_LABELS: dict[str, str] = {
    "ja": "日本語",
    "en": "English",
}


def t(key: str, lang: str | None = None) -> str:
    """指定された言語の文字列を返す。未定義時は ja にフォールバック。"""
    if lang is None:
        lang = "ja"
    if lang not in STRINGS:
        lang = "ja"
    return STRINGS[lang].get(key, STRINGS["ja"].get(key, key))


def get_language_labels() -> dict[str, str]:
    """認識言語の表示名辞書 {code: label} を返す。"""
    return dict(_LANGUAGES_LABELS)


def get_ui_language_labels() -> dict[str, str]:
    """UI 言語の表示名辞書 {code: label} を返す。"""
    return dict(_UI_LANGUAGES_LABELS)
