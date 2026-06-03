"""macOS 入力ソース切り替えユーティリティ

日本語IME → 英数モードの切り替え・復元を行う。

英数/かなキーを osascript (System Events) 経由でシミュレートする。
osascript は別プロセスなので pynput の event tap に傍受されず、
確実に IME を切り替えられる。
"""

import subprocess
from AppKit import NSBundle
import objc


# ── Carbon framework（TIS 読み取り専用関数のみ） ──────────────────

_CarbonBundle = NSBundle.bundleWithPath_(
    "/System/Library/Frameworks/Carbon.framework"
)
if not _CarbonBundle.isLoaded():
    _CarbonBundle.load()

_TIS_READ_FUNCTIONS = [
    ("TISCopyCurrentKeyboardInputSource", b"@"),
    ("TISGetInputSourceProperty", b"@@@"),
]
_TIS_CONSTANTS = [
    ("kTISPropertyInputSourceID", b"@"),
    ("kTISPropertyInputModeID", b"@"),
    ("kTISPropertyBundleID", b"@"),
]

objc.loadBundleFunctions(_CarbonBundle, globals(), _TIS_READ_FUNCTIONS)
objc.loadBundleVariables(_CarbonBundle, globals(), _TIS_CONSTANTS)


# ── 日本語入力モード検出 ───────────────────────────────────────────

def _is_japanese_input_mode(source) -> bool:
    if source is None:
        return False
    mode_id = TISGetInputSourceProperty(source, kTISPropertyInputModeID)
    if mode_id and "Japanese" in str(mode_id):
        return True
    bundle_id = TISGetInputSourceProperty(source, kTISPropertyBundleID)
    if bundle_id and "Kotoeri" in str(bundle_id):
        return True
    return False


def _osascript_keycode(keycode: int) -> None:
    """osascript 経由でキーコードを System Events に送信。

    別プロセスなので pynput event tap に傍受されず、確実に IME 切替される。
    """
    try:
        subprocess.run(
            ["osascript", "-e",
             f'tell application "System Events" to key code {keycode}'],
            capture_output=True, timeout=2,
        )
    except Exception:
        pass


# ── 公開 API ───────────────────────────────────────────────────────

def save_and_switch_to_ascii() -> bool:
    """日本語IME が有効なら osascript で英数キーを投入して ASCII に切替。

    Returns:
        True なら復元が必要（元が日本語IMEだった）。
        False なら既に英数モード（復元不要）。
    """
    current = TISCopyCurrentKeyboardInputSource()
    if current is None:
        return False
    if not _is_japanese_input_mode(current):
        return False

    _osascript_keycode(102)  # kVK_JIS_Eisu
    return True


def restore_to_kana() -> None:
    """かなキーを osascript で投入して日本語IME に復元。"""
    _osascript_keycode(104)  # kVK_JIS_Kana
