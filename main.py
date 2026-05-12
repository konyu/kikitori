#!/usr/bin/env python3
"""
Voice to Text Injection Tool
Apple Silicon Mac向け音声認識ツール

ホットキー押下中にマイク入力を録音し、
解放時に音声認識結果をクリップボード経由でペーストします。

デフォルトホットキー: Caps Lock（設定ファイルで変更可能）
"""

from voice_to_text.app import App


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
