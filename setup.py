from setuptools import setup

APP = ["menu_bar_app.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": True,
    "packages": [
        "voice_to_text",
        "rumps",
        "pynput",
        "sounddevice",
        "mlx_whisper",
        "pyperclip",
        "numpy",
    ],
    "includes": [
        "threading",
        "json",
        "pathlib",
    ],
    "plist": {
        "CFBundleName": "VoiceToText",
        "CFBundleDisplayName": "VoiceToText",
        "CFBundleIdentifier": "com.example.voicetotext",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSMicrophoneUsageDescription": (
            "ホットキー押下中の音声入力を録音するためにマイクへのアクセスが必要です。"
        ),
        "NSAccessibilityUsageDescription": (
            "音声認識結果をアクティブなアプリに自動入力するためにアクセシビリティ権限が必要です。"
        ),
        "LSUIElement": True,  # Dock アイコンを非表示にしてメニューバー専用アプリ化
    },
    # sounddevice の PortAudio dylib を含めるための設定
    "resources": [],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
