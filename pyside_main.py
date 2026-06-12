#!/usr/bin/env python3
"""
Kikitori - PySide6 版エントリーポイント
画面中央下に音声入力中オーバーレイUIを表示
"""
import sys

if "--version" in sys.argv:
    from kikitori.config import VERSION
    print(f"Kikitori {VERSION}")
    sys.exit(0)

from kikitori.ui_pyside import main

if __name__ == "__main__":
    main()
