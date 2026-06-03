#!/usr/bin/env python3
"""
Kikitori - PySide6 版エントリーポイント
画面中央下に音声入力中オーバーレイUIを表示
"""
import os
os.environ["QT_LOGGING_RULES"] = "qt.text.font.db.warning=false"

from kikitori.ui_pyside import main

if __name__ == "__main__":
    main()
