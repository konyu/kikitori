"""py2app setup for Kikitori"""
from setuptools import setup

# データファイル（アイコンなど）
DATA_FILES = [
    ("assets", ["assets/icon-idle.png", "assets/icon-recording.png"]),
]

# py2app オプション
OPTIONS = {
    "argv_emulation": False,
    "packages": ["kikitori", "mlx_whisper", "sounddevice", "numpy", "pynput", "pyperclip", "yaml"],
    "includes": ["AppKit", "Foundation", "objc"],
    "plist": {
        "CFBundleName": "Kikitori",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "CFBundleIdentifier": "com.kikitori.app",
        "LSUIElement": True,  # ★ Dock非表示 + メニューバー常駐
        "NSMicrophoneUsageDescription": "音声入力のためマイクにアクセスします。",
        "NSAccessibilityUsageDescription": "ホットキー監視と自動ペーストのためアクセシビリティ権限が必要です。",
    },
    "iconfile": None,  # .icnsファイルがあれば指定
}

setup(
    name="Kikitori",
    app=["pyside_main.py"],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
