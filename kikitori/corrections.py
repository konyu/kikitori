"""校正辞書管理（~/.kikitori/corrections.yaml）

Whisper 音声認識結果に対し、ユーザー定義の「間違い→訂正」ペアを
ケースインセンシティブかつ長いキー優先で適用する。
"""
import re
from pathlib import Path

import yaml

CORRECTIONS_PATH: Path = Path.home() / ".kikitori" / "corrections.yaml"

TEMPLATE = """# Kikitori 校正辞書
# Whisper の音声認識結果に対し、以下の「間違い: 訂正」ペアを自動適用します。
# 大文字小文字は無視して置換されます（例: "Use Effect" も "useEffect" に変換）。
# 長いフレーズが短い単語より優先して置換されます。

use effect: useEffect
"""


class Corrections:
    """校正辞書を読み込み、STT 結果文字列に適用する。

    path 引数でファイルパスを指定可能（デフォルト: ~/.kikitori/corrections.yaml）。
    依存注入によるテストが容易な設計。
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path if path is not None else CORRECTIONS_PATH
        self._items: dict[str, str] = {}

    def load(self) -> None:
        """YAML ファイルから校正ペアを読み込む。

        ファイルが存在しない、または YAML のパースに失敗した場合は空辞書になる。
        """
        if not self._path.exists():
            self._items = {}
            return

        try:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except Exception as e:
            import sys
            print(
                f"[WARN] 校正辞書ファイルの読み込みに失敗しました: {self._path} — {e}",
                file=sys.stderr,
            )
            self._items = {}
            return

        if isinstance(data, dict):
            # "corrections:" キーがあればその中身を使い、なければルートをそのまま使う
            if "corrections" in data and isinstance(data["corrections"], dict):
                raw = data["corrections"]
            else:
                raw = data
            # None 値を除外し、キー・値を両方 str に正規化
            self._items = {
                str(k).strip(): str(v)
                for k, v in raw.items()
                if k is not None and v is not None
            }
        else:
            self._items = {}

    def correct(self, text: str) -> str:
        """ロードしたマッピングに基づき、長いキーから順にケースインセンシティブ置換する。

        一度置換した部分は再度置換されない（連鎖置換を防ぐ）。
        置換結果は常に correction 側の文字列が挿入される。
        """
        if not self._items or not text:
            return text

        sorted_items = sorted(self._items.items(), key=lambda x: len(x[0]), reverse=True)
        result: list[str] = []
        i = 0
        while i < len(text):
            matched = False
            for wrong, right in sorted_items:
                end = i + len(wrong)
                if end <= len(text) and text[i:end].lower() == wrong.lower():
                    result.append(right)
                    i = end
                    matched = True
                    break
            if not matched:
                result.append(text[i])
                i += 1
        return "".join(result)

    def get_items(self) -> dict[str, str]:
        """現在の校正ペア辞書を返す（コピー）。"""
        return dict(self._items)

    def save_items(self, items: dict[str, str]) -> None:
        """校正ペア辞書を YAML ファイルに保存し、内部状態も更新する。"""
        self._items = dict(items)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                yaml.dump(
                    {"corrections": self._items},
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            import sys
            print(
                f"[WARN] 校正辞書ファイルの書き込みに失敗しました: {self._path} — {e}",
                file=sys.stderr,
            )

    @staticmethod
    def generate_template() -> str:
        """雛形 YAML 文字列を返す。"""
        return TEMPLATE

    @property
    def path(self) -> Path:
        """校正辞書ファイルのパスを返す。"""
        return self._path
