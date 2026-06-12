"""専門用語リスト管理（~/.kikitori/glossary.yaml）

Whisper 音声認識の initial_prompt に専門用語を追記し、
認識精度を向上させるための用語集を管理する。
"""
from pathlib import Path

GLOSSARY_PATH: Path = Path.home() / ".kikitori" / "glossary.yaml"

TEMPLATE = """# Kikitori 用語集
# Whisper 音声認識の補助として initial_prompt に自動追記されます。
# 行頭に "- " を付けて1行1用語で記述してください。
#
# 例:
# terms:
#   - MLX
#   - Transformer
#   - Apple Silicon

terms: []
"""


class Glossary:
    """専門用語リストを読み込み、Whisper の initial_prompt に追記する。

    path 引数でファイルパスを指定可能（デフォルト: ~/.kikitori/glossary.yaml）。
    依存注入によるテストが容易な設計。
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path if path is not None else GLOSSARY_PATH
        self._terms: list[str] = []

    def load(self) -> None:
        """YAML ファイルから用語リストを読み込む。

        ファイルが存在しない、または YAML のパースに失敗した場合は空リストになる。
        """
        if not self._path.exists():
            self._terms = []
            return

        try:
            import yaml
            data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except Exception as e:
            import sys
            print(f"[WARN] 用語集ファイルの読み込みに失敗しました: {self._path} — {e}", file=sys.stderr)
            self._terms = []
            return

        if isinstance(data, dict) and "terms" in data and isinstance(data["terms"], list):
            self._terms = [str(t) for t in data["terms"] if t is not None]
        else:
            self._terms = []

    def get_terms(self) -> list[str]:
        """現在の用語リストを返す。"""
        return list(self._terms)

    def build_prompt(self, base_prompt: str) -> str:
        """base_prompt の末尾に用語を追記したプロンプト文字列を返す。

        用語が空の場合は base_prompt をそのまま返す。
        用語がある場合は「。専門用語: 用語1, 用語2, ...」を追記する。
        base_prompt が句点で終わっている場合は重複を避ける。
        """
        if not self._terms:
            return base_prompt

        terms_str = ", ".join(self._terms)
        # base_prompt が空でなければ句点で区切る
        if base_prompt:
            if base_prompt.rstrip().endswith("。"):
                return f"{base_prompt}専門用語: {terms_str}"
            return f"{base_prompt}。専門用語: {terms_str}"
        else:
            return f"専門用語: {terms_str}"

    @staticmethod
    def generate_template() -> str:
        """雛形 YAML 文字列を返す。"""
        return TEMPLATE

    @property
    def path(self) -> Path:
        """用語集ファイルのパスを返す。"""
        return self._path
