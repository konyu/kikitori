"""py2app setup for Kikitori"""
import sys

# py2appの依存解析で再帰が深くなるため上限を上げる
sys.setrecursionlimit(10000)

from setuptools import setup

# データファイル（アイコンなど）
DATA_FILES = [
    ("assets", ["assets/dock-icon.png", "assets/icon-idle.png", "assets/icon-recording.png"]),
    ("_sounddevice_data/portaudio-binaries", [
        "/Users/kon_yu/development/whisper/venv/lib/python3.13/site-packages/_sounddevice_data/portaudio-binaries/libportaudio.dylib"
    ]),
]

# py2app オプション
OPTIONS = {
    "argv_emulation": False,
    "packages": ["kikitori", "sounddevice", "numpy", "pynput", "pyperclip", "yaml"],
    "includes": ["AppKit", "Foundation", "objc"],
    "excludes": ["PyInstaller", "pytest", "tkinter", "matplotlib", "PIL", "django", "scipy"],
    "plist": {
        "CFBundleName": "Kikitori",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "CFBundleIdentifier": "com.kikitori.app",
        "LSUIElement": True,  # ★ Dock非表示 + メニューバー常駐
        "NSMicrophoneUsageDescription": "音声入力のためマイクにアクセスします。",
        "NSAccessibilityUsageDescription": "ホットキー監視と自動ペーストのためアクセシビリティ権限が必要です。",
    },
    "iconfile": None,
}

setup(
    name="Kikitori",
    app=["pyside_main.py"],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    zipfile=None,  # zip圧縮を無効にして.dylibを正しく配置
)
