"""macOS 入力ソース切り替えユーティリティ

日本語IME → 英数モードの切り替え・復元を行う。

TIS API はメインスレッド専用で pynput のコールバックスレッドから
安全に呼べないため、CGEventPost によるキーボードイベントシミュレーション
方式を使用する。英数キー（kVK_JIS_Eisu = 102）のキーコードを
CGEventPost でシステムに投入する。

この方式は pynput の event tap スレッドから安全に呼べ、クラッシュしない。
"""

from AppKit import NSBundle
import objc

# ── HIToolbox / CoreGraphics フレームワーク読み込み ─────────────────

_CarbonBundle = NSBundle.bundleWithPath_(
    "/System/Library/Frameworks/Carbon.framework"
)
if not _CarbonBundle.isLoaded():
    _CarbonBundle.load()

# TIS 関数（読み取り専用のためスレッドセーフ）
_TIS_READ_FUNCTIONS = [
    ("TISCopyCurrentKeyboardInputSource", b"@"),
    ("TISGetInputSourceProperty", b"@@@"),
    ("TISCreateInputSourceList", b"@@B"),
]
_TIS_CONSTANTS = [
    ("kTISPropertyInputSourceType", b"@"),
    ("kTISPropertyInputSourceID", b"@"),
    ("kTISPropertyInputModeID", b"@"),
    ("kTISPropertyBundleID", b"@"),
    ("kTISTypeKeyboardLayout", b"@"),
    ("kTISTypeKeyboardInputMode", b"@"),
]

objc.loadBundleFunctions(_CarbonBundle, globals(), _TIS_READ_FUNCTIONS)
objc.loadBundleVariables(_CarbonBundle, globals(), _TIS_CONSTANTS)

# CGEventPost によるキーボードイベント投入（スレッドセーフ）
try:
    _QuartzBundle = NSBundle.bundleWithPath_(
        "/System/Library/Frameworks/Quartz.framework"
    )
    if not _QuartzBundle.isLoaded():
        _QuartzBundle.load()

    _QUARTZ_FUNCTIONS = [
        ("CGEventCreateKeyboardEvent", b"@@H{Bool=B}"),
        ("CGEventPost", b"vII"),
    ]
    objc.loadBundleFunctions(_QuartzBundle, globals(), _QUARTZ_FUNCTIONS)
    _HAS_CGEVENT = True
except Exception:
    _HAS_CGEVENT = False

# ── キーコード定数 ─────────────────────────────────────────────────

kVK_JIS_Eisu = 102          # 英数キー（スペース左）
kVK_JIS_Kana = 104          # かなキー（スペース右）

kCGHIDEventTap = 0


# ── 英数/かな 切り替え ─────────────────────────────────────────────

def _post_key_event(keycode: int, keydown: bool) -> None:
    """CGEventPost でキーイベントをシステムに投入する。

    CGEventPost はスレッドセーフ。バックグラウンドスレッドから安全に呼べる。
    """
    if not _HAS_CGEVENT:
        return

    event = CGEventCreateKeyboardEvent(None, keycode, keydown)
    CGEventPost(kCGHIDEventTap, event)


def switch_to_ascii() -> None:
    """英数キーイベントを投入し、英数モードに切り替える。"""
    if not _HAS_CGEVENT:
        return
    _post_key_event(kVK_JIS_Eisu, True)
    _post_key_event(kVK_JIS_Eisu, False)


def switch_to_kana() -> None:
    """かなキーイベントを投入し、かなモードに切り替える。"""
    if not _HAS_CGEVENT:
        return
    _post_key_event(kVK_JIS_Kana, True)
    _post_key_event(kVK_JIS_Kana, False)


# ── 日本語入力モード検出（TIS 読み取り専用、スレッドセーフ） ────

def _is_japanese_input_mode(source) -> bool:
    """指定された入力ソースが日本語入力モードか判定。"""
    if source is None:
        return False

    mode_id = TISGetInputSourceProperty(source, kTISPropertyInputModeID)
    if mode_id and "Japanese" in str(mode_id):
        return True

    bundle_id = TISGetInputSourceProperty(source, kTISPropertyBundleID)
    if bundle_id and "Kotoeri" in str(bundle_id):
        return True

    return False


# ── 公開 API ───────────────────────────────────────────────────────

def get_current_input_source_id() -> str | None:
    """現在の入力ソースIDを取得。"""
    current = TISCopyCurrentKeyboardInputSource()
    if current is None:
        return None
    sid = TISGetInputSourceProperty(current, kTISPropertyInputSourceID)
    return str(sid) if sid else None

def save_and_switch_to_ascii() -> bool:
    """日本語IME が有効なら英数キーで英数モードに切り替える。

    読み取り専用の TIS 関数で状態を確認し、切り替えが必要な場合は
    CGEventPost で英数キーをシミュレートする。スレッドセーフ。

    Returns:
        True なら復元が必要（元が日本語IMEだった）。
        False なら既に英数モード（復元不要）。
    """
    current = TISCopyCurrentKeyboardInputSource()
    if current is None:
        return False

    if not _is_japanese_input_mode(current):
        return False

    switch_to_ascii()
    return True

def restore_to_kana() -> None:
    """かなキーイベントを投入し、かなモードに復元する。"""
    switch_to_kana()
