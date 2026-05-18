"""Glossary のテスト — 用語集の読み込み・プロンプト生成・雛形検証"""
import tempfile
from pathlib import Path

import pytest
import yaml

from kikitori.glossary import GLOSSARY_PATH, TEMPLATE, Glossary


class TestGlossary:
    def test_load_empty_when_no_file(self):
        """存在しないパスでは load() 後 get_terms() が空リストを返す。"""
        glossary = Glossary(path=Path("/tmp/nonexistent_glossary_test.yaml"))
        glossary.load()
        assert glossary.get_terms() == []

    def test_load_reads_terms(self):
        """YAML ファイルから用語リストを正しく読み込む。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("terms:\n  - MLX\n  - Transformer\n  - Apple Silicon\n")
            tmp_path = Path(f.name)

        try:
            glossary = Glossary(path=tmp_path)
            glossary.load()
            assert glossary.get_terms() == ["MLX", "Transformer", "Apple Silicon"]
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_load_empty_terms_list(self):
        """terms が空リストの YAML を読み込む。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("terms: []\n")
            tmp_path = Path(f.name)

        try:
            glossary = Glossary(path=tmp_path)
            glossary.load()
            assert glossary.get_terms() == []
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_load_no_terms_key(self):
        """terms キーがない YAML は空リストになる。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("language: ja\n")
            tmp_path = Path(f.name)

        try:
            glossary = Glossary(path=tmp_path)
            glossary.load()
            assert glossary.get_terms() == []
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_build_prompt_with_terms(self):
        """用語がある場合、base_prompt の末尾に「。専門用語: ...」が追記される。"""
        glossary = Glossary(path=Path("/tmp/nonexistent.yaml"))
        glossary._terms = ["MLX", "Transformer"]
        result = glossary.build_prompt("以下は日本語の音声認識結果です。")
        # base_prompt が句点で終わっているので重複しない
        assert result == "以下は日本語の音声認識結果です。専門用語: MLX, Transformer"

    def test_build_prompt_empty_terms(self):
        """用語が空の場合、base_prompt がそのまま返る。"""
        glossary = Glossary(path=Path("/tmp/nonexistent.yaml"))
        glossary._terms = []
        result = glossary.build_prompt("base")
        assert result == "base"

    def test_build_prompt_empty_base_with_terms(self):
        """base_prompt が空で用語がある場合、「専門用語: ...」のみ返る。"""
        glossary = Glossary(path=Path("/tmp/nonexistent.yaml"))
        glossary._terms = ["MLX"]
        result = glossary.build_prompt("")
        assert result == "専門用語: MLX"

    def test_build_prompt_single_term(self):
        """用語が1つだけの場合も正しく追記される。"""
        glossary = Glossary(path=Path("/tmp/nonexistent.yaml"))
        glossary._terms = ["Apple Silicon"]
        result = glossary.build_prompt("base")
        assert result == "base。専門用語: Apple Silicon"

    def test_generate_template(self):
        """雛形に \"terms:\" とコメントが含まれる。"""
        template = Glossary.generate_template()
        assert "terms:" in template
        assert "#" in template
        assert "Kikitori 用語集" in template

    def test_generate_template_is_valid_yaml(self):
        """雛形が有効な YAML として読み込める。"""
        template = Glossary.generate_template()
        data = yaml.safe_load(template)
        assert isinstance(data, dict)
        assert "terms" in data
        assert data["terms"] == []

    def test_load_malformed_yaml_does_not_crash(self):
        """不正な YAML でも例外が発生せず空リストになる。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(": invalid yaml : :\n")
            tmp_path = Path(f.name)

        try:
            glossary = Glossary(path=tmp_path)
            glossary.load()  # 例外が発生しない
            assert glossary.get_terms() == []
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_build_prompt_with_special_chars(self):
        """特殊文字を含む用語でも正しく追記される。"""
        glossary = Glossary(path=Path("/tmp/nonexistent.yaml"))
        glossary._terms = ["C++", "C#", "F#"]
        result = glossary.build_prompt("base")
        assert "C++" in result
        assert "C#" in result
        assert "F#" in result
        assert result == "base。専門用語: C++, C#, F#"

    def test_load_filters_none_values(self):
        """YAML に None 値が混ざっていても無視される。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("terms:\n  - MLX\n  -\n  - Transformer\n")
            tmp_path = Path(f.name)

        try:
            glossary = Glossary(path=tmp_path)
            glossary.load()
            assert glossary.get_terms() == ["MLX", "Transformer"]
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_path_property(self):
        """path プロパティが正しいパスを返す。"""
        glossary = Glossary(path=Path("/custom/path.yaml"))
        assert glossary.path == Path("/custom/path.yaml")

    def test_default_path(self):
        """デフォルトパスが GLOSSARY_PATH 定数と一致する。"""
        glossary = Glossary()
        assert glossary.path == GLOSSARY_PATH

    def test_get_terms_returns_copy(self):
        """get_terms() が内部リストのコピーを返す（変更しても内部に影響しない）。"""
        glossary = Glossary(path=Path("/tmp/nonexistent.yaml"))
        glossary._terms = ["term1", "term2"]
        terms = glossary.get_terms()
        terms.append("term3")
        assert glossary.get_terms() == ["term1", "term2"]
