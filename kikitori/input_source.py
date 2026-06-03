"""macOS 入力ソース切り替えユーティリティ

日本語IME → 英数モードの切り替え・復元を行う。

TIS API はスレッドセーフでない（Carbon API はメインスレッド専用）。
pynput のイベントタップスレッドなど任意のスレッドから安全に呼べるよう、
performSelectorOnMainThread でメインスレッドに委譲する。
"""

from Foundation import NSObject, NSBundle
import objc
import threading

# ── メインスレッド委譲ヘルパー ──────────────────────────────────────

class _MainThreadRunner(NSObject):
    """Python callable をメインスレッドで同期的に実行する ObjC ヘルパー。"""
    
    def init(self):
        self = objc.super(_MainThreadRunner, self).init()
        self._callback = None
        return self
    
    def setCallback_(self, cb):
        self._callback = cb
    
    def invoke_(self, sender):
        self._callback()

_runner = _MainThreadRunner.alloc().init()

def _on_main_thread(cb):
    """callable cb をメインスレッドで同期的に実行する。
    
    既にメインスレッドの場合はそのまま実行。
    そうでなければ performSelectorOnMainThread で委譲。
    """
    import threading as _threading
    if _threading.current_thread() is _threading.main_thread():
        return cb()
    
    result = [None]
    exception = [None]
    
    def wrapped():
        try:
            result[0] = cb()
        except Exception as e:
            exception[0] = e
    
    _runner.setCallback_(wrapped)
    _runner.performSelectorOnMainThread_withObject_waitUntilDone_(
        "invoke:", None, True
    )
    
    if exception[0] is not None:
        raise exception[0]
    return result[0]

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
_ascii_source = None
_japanese_source = None
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

    メインスレッドで同期的に実行し、任意のスレッドから安全に呼べる。

    Returns:
        True なら復元が必要（元が日本語IMEだった）。
        False なら既に英数モード（復元不要）。
    """
    def _do() -> bool:
        current = TISCopyCurrentKeyboardInputSource()
        if current is None:
            return False
        if not _is_japanese_input_mode(current):
            return False
        _init_cache()
        if _ascii_source is not None:
            TISSelectInputSource(_ascii_source)
        return True

    return _on_main_thread(_do)

def restore_to_kana() -> None:
    """日本語IME に復元する。

    メインスレッドで同期的に実行し、任意のスレッドから安全に呼べる。
    """
    def _do():
        _init_cache()
        if _japanese_source is not None:
            TISSelectInputSource(_japanese_source)

    _on_main_thread(_do)
