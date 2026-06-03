"""macOS 入力ソース切り替えユーティリティ

日本語IME → 英数モードの切り替え・復元を行う。

TISSelectInputSource API を使用して直接入力ソースを切り替える。
キーイベントを生成しないため pynput event tap に傍受されず、
スレッドセーフに動作する。
"""

from AppKit import NSBundle
import objc
import threading

# ── Carbon framework ───────────────────────────────────────────────

_CarbonBundle = NSBundle.bundleWithPath_(
    "/System/Library/Frameworks/Carbon.framework"
)
if not _CarbonBundle.isLoaded():
    _CarbonBundle.load()

_TIS_FUNCTIONS = [
    ("TISCopyCurrentKeyboardInputSource", b"@"),
    ("TISGetInputSourceProperty", b"@@@"),
    ("TISCreateInputSourceList", b"@@B"),
    ("TISSelectInputSource", b"v@"),
]
_TIS_CONSTANTS = [
    ("kTISPropertyInputSourceID", b"@"),
    ("kTISPropertyInputModeID", b"@"),
    ("kTISPropertyBundleID", b"@"),
]

objc.loadBundleFunctions(_CarbonBundle, globals(), _TIS_FUNCTIONS)
objc.loadBundleVariables(_CarbonBundle, globals(), _TIS_CONSTANTS)

# ── 入力ソースキャッシュ ───────────────────────────────────────────

_cache_lock = threading.Lock()
_ascii_source = None  # type: ignore
_japanese_source = None  # type: ignore
_cache_initialized = False


def _init_cache() -> None:
    """システムの入力ソース一覧から ASCII と日本語IME を検索・キャッシュ。"""
    global _ascii_source, _japanese_source, _cache_initialized

    with _cache_lock:
        if _cache_initialized:
            return
        all_sources = TISCreateInputSourceList(None, True)
        if all_sources:
            for src in all_sources:
                sid = TISGetInputSourceProperty(src, kTISPropertyInputSourceID)
                if sid is None:
                    continue
                sid_str = str(sid)
                if _ascii_source is None and "keylayout.ABC" in sid_str:
                    _ascii_source = src
                if _japanese_source is None and "Kotoeri" in sid_str and (
                    "Japanese" in sid_str or "Hiragana" in sid_str
                ):
                    _japanese_source = src
                if _ascii_source is not None and _japanese_source is not None:
                    break
        _cache_initialized = True


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


# ── 公開 API ───────────────────────────────────────────────────────

def save_and_switch_to_ascii() -> bool:
    """日本語IME が有効なら ASCII に切り替える。

    Returns:
        True なら復元が必要（元が日本語IMEだった）。
        False なら既に英数モード（復元不要）。
    """
    # TISCopyCurrentKeyboardInputSource が TSM Mach port エラーを
    # 出し得るが、結果は正しく返る。エラーは無視して続行。
    current = TISCopyCurrentKeyboardInputSource()
    if current is None:
        return False
    if not _is_japanese_input_mode(current):
        return False

    _init_cache()
    if _ascii_source is not None:
        TISSelectInputSource(_ascii_source)
    return True


def restore_to_kana() -> None:
    """日本語IME に復元する。"""
    _init_cache()
    if _japanese_source is not None:
        TISSelectInputSource(_japanese_source)



