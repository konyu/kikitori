"""設定管理と macOS ユーティリティのテスト"""
import tempfile
from pathlib import Path

import pytest

from kikitori.settings import (
    SETTINGS_PATH,
    load_settings,
    save_settings,
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


class TestMacOSUtils:
    def test_get_frontmost_pid_returns_int_or_none(self):
        """PID が整数または None で返る"""
        pid = get_frontmost_pid()
        # macOS では通常 PID が取れる。取れない場合も None が返るだけ。
        assert pid is None or isinstance(pid, int)

    def test_activate_app_by_pid_invalid_returns_false(self):
        """存在しない PID に対しては False を返す"""
        result = activate_app_by_pid(99999999)
        assert result is False
