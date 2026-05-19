"""Corrections のテスト — 校正辞書の読み込み・ケースインセンシティブ置換・順序制御"""
import tempfile
from pathlib import Path

import pytest
import yaml

from kikitori.corrections import CORRECTIONS_PATH, TEMPLATE, Corrections


class TestCorrections:
    def test_load_empty_when_no_file(self):
        """存在しないパスでは load() 後 get_items() が空辞書を返す。"""
        corr = Corrections(path=Path("/tmp/nonexistent_corrections_test.yaml"))
        corr.load()
        assert corr.get_items() == {}

    def test_load_reads_items(self):
        """YAML ファイルから校正ペアを正しく読み込む。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("use effect: useEffect\nreact: React\n")
            tmp_path = Path(f.name)

        try:
            corr = Corrections(path=tmp_path)
            corr.load()
            assert corr.get_items() == {"use effect": "useEffect", "react": "React"}
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_load_with_corrections_key(self):
        """corrections: キーでネストされた YAML を読み込む。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("corrections:\n  use effect: useEffect\n")
            tmp_path = Path(f.name)

        try:
            corr = Corrections(path=tmp_path)
            corr.load()
            assert corr.get_items() == {"use effect": "useEffect"}
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_load_empty_dict(self):
        """空辞書の YAML を読み込む。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("{}\n")
            tmp_path = Path(f.name)

        try:
            corr = Corrections(path=tmp_path)
            corr.load()
            assert corr.get_items() == {}
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_load_malformed_yaml_does_not_crash(self):
        """不正な YAML でも例外が発生せず空辞書になる。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(": invalid yaml : :\n")
            tmp_path = Path(f.name)

        try:
            corr = Corrections(path=tmp_path)
            corr.load()
            assert corr.get_items() == {}
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_correct_single_pair(self):
        """単一ペアの置換が正しく動作する。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        corr._items = {"use effect": "useEffect"}
        assert corr.correct("use effect") == "useEffect"

    def test_correct_case_insensitive(self):
        """大文字小文字を無視して置換する。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        corr._items = {"use effect": "useEffect"}
        assert corr.correct("Use Effect") == "useEffect"
        assert corr.correct("USE EFFECT") == "useEffect"
        assert corr.correct("uSe EfFeCt") == "useEffect"

    def test_correct_longest_first(self):
        """長いキーが短いキーより先に置換される。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        corr._items = {"use": "ユーザ", "use effect": "useEffect"}
        # "use effect" が先に置換され、"use" にはマッチしない
        assert corr.correct("use effect") == "useEffect"

    def test_correct_partial_match(self):
        """部分文字列でも置換される。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        corr._items = {"use": "ユーザ"}
        assert corr.correct("reuse") == "reユーザ"

    def test_correct_multiple_pairs(self):
        """複数ペアが順に適用される。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        corr._items = {"use effect": "useEffect", "state": "State"}
        assert corr.correct("use effect and state") == "useEffect and State"

    def test_correct_empty_text(self):
        """空文字はそのまま返る。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        corr._items = {"use": "ユーザ"}
        assert corr.correct("") == ""

    def test_correct_no_items(self):
        """空辞書の場合、テキストはそのまま返る。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        assert corr.correct("hello world") == "hello world"

    def test_save_items(self):
        """save_items() で YAML ファイルに保存される。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            tmp_path = Path(f.name)

        try:
            corr = Corrections(path=tmp_path)
            corr.save_items({"use effect": "useEffect", "react": "React"})

            content = tmp_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            assert data == {"corrections": {"use effect": "useEffect", "react": "React"}}

            # 内部状態も更新されている
            assert corr.get_items() == {"use effect": "useEffect", "react": "React"}
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_get_items_returns_copy(self):
        """get_items() が内部辞書のコピーを返す。"""
        corr = Corrections(path=Path("/tmp/nonexistent.yaml"))
        corr._items = {"a": "b"}
        items = corr.get_items()
        items["c"] = "d"
        assert corr.get_items() == {"a": "b"}

    def test_generate_template(self):
        """雛形にコメントとペアが含まれる。"""
        template = Corrections.generate_template()
        assert "use effect: useEffect" in template
        assert "校正辞書" in template

    def test_default_path(self):
        """デフォルトパスが CORRECTIONS_PATH と一致する。"""
        corr = Corrections()
        assert corr.path == CORRECTIONS_PATH

    def test_custom_path(self):
        """path 引数が正しく設定される。"""
        custom = Path("/custom/corrections.yaml")
        corr = Corrections(path=custom)
        assert corr.path == custom
