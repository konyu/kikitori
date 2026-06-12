"""設定管理と macOS ユーティリティのテスト"""
import tempfile
from pathlib import Path

import pytest

from kikitori.settings import (
    SETTINGS_PATH,
    detect_os_language,
    get_ui_language,
    load_settings,
    save_settings,
    reset_settings,
    get_frontmost_pid,
    activate_app_by_pid,
)


class TestSettingsIO:
    def test_load_settings_returns_empty_when_no_file(self, monkeypatch):
        """設定ファイルが存在しない場合は空辞書を返す"""
        tmp = tempfile.mktemp(suffix=".yaml")
        monkeypatch.setattr("kikitori.settings.SETTINGS_PATH", Path(tmp))
        assert load_settings() == {}

    def test_save_and_load_roundtrip(self, monkeypatch):
        """保存→読み込みで同じデータが復元される"""
        tmp = tempfile.mktemp(suffix=".yaml")
        monkeypatch.setattr("kikitori.settings.SETTINGS_PATH", Path(tmp))
        data = {"language": "ja", "prompt": "テスト", "hotkey": ["ctrl", "alt"]}
        save_settings(data)
        loaded = load_settings()
        assert loaded == data

    def test_load_corrupted_file_returns_empty(self, monkeypatch, tmp_path):
        """破損した YAML ファイルは空辞書を返す（エラーを起こさない）"""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text(": invalid: yaml: [")
        monkeypatch.setattr("kikitori.settings.SETTINGS_PATH", bad_file)
        assert load_settings() == {}

    def test_save_does_not_raise_on_permission_error(self, monkeypatch):
        """保存エラー時も例外を送出しない"""

        class BrokenPath:
            def write_text(self, *args, **kwargs):
                raise PermissionError("denied")

        monkeypatch.setattr("kikitori.settings.SETTINGS_PATH", BrokenPath())
        # 例外が発生しないこと
        save_settings({"key": "value"})

    def test_reset_settings_deletes_file(self, monkeypatch):
        """reset_settings で設定ファイルが削除される"""
        tmp = tempfile.mktemp(suffix=".yaml")
        path = Path(tmp)
        monkeypatch.setattr("kikitori.settings.SETTINGS_PATH", path)
        save_settings({"language": "en", "prompt": "test"})
        assert path.exists()
        reset_settings()
        assert not path.exists()
        assert load_settings() == {}

    def test_reset_settings_does_not_raise_when_missing(self, monkeypatch):
        """設定ファイルが存在しなくても reset_settings は例外を出さない"""
        tmp = tempfile.mktemp(suffix=".yaml")
        path = Path(tmp)
        monkeypatch.setattr("kikitori.settings.SETTINGS_PATH", path)
        assert not path.exists()
        # 例外が発生しないこと
        reset_settings()


class TestMacOSUtils:
    def test_detect_os_language_ja(self):
        """OS言語が日本語なら 'ja' を返す"""
        assert detect_os_language(lambda: ["ja-JP"]) == "ja"

    def test_detect_os_language_en(self):
        """OS言語が英語なら 'en' を返す"""
        assert detect_os_language(lambda: ["en-US"]) == "en"

    def test_detect_os_language_other_falls_back_to_en(self):
        """日本語以外の言語は 'en' にフォールバック"""
        assert detect_os_language(lambda: ["fr-FR"]) == "en"

    def test_detect_os_language_fallback_on_error(self):
        """NSLocale 取得失敗時は 'en' にフォールバック"""
        def broken():
            raise RuntimeError("simulated failure")
        assert detect_os_language(broken) == "en"

    def test_get_ui_language_from_settings(self):
        """設定ファイルの ui_language が最優先"""
        assert get_ui_language({"ui_language": "ja"}) == "ja"
        assert get_ui_language({"ui_language": "en"}) == "en"

    def test_get_ui_language_falls_back_to_os(self):
        """設定なし → OS 検出（locale_getter 経由）"""
        # get_ui_language は detect_os_language() を呼ぶ（依存注入なし）
        # 実 OS 言語が返るので ja/en のいずれか
        result = get_ui_language({})
        assert result in ("ja", "en")

    def test_get_ui_language_none_settings(self):
        """settings=None でも OS 検出で解決"""
        result = get_ui_language(None)
        assert result in ("ja", "en")

    def test_get_frontmost_pid_returns_int_or_none(self):
        """PID が整数または None で返る"""
        pid = get_frontmost_pid()
        # macOS では通常 PID が取れる。取れない場合も None が返るだけ。
        assert pid is None or isinstance(pid, int)

    def test_activate_app_by_pid_invalid_returns_false(self):
        """存在しない PID に対しては False を返す"""
        result = activate_app_by_pid(99999999)
        assert result is False
