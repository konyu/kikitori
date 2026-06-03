"""macOS のバックグラウンドスレッドで AppKit を安全に呼ぶためのユーティリティ"""
import contextlib

@contextlib.contextmanager
def macos_thread_runloop():
    """
    バックグラウンドスレッドで AppKit/InputMethodKit を呼ぶ際に
    Mach port (IMKCFRunLoopWakeUpReliable) エラーを防ぐコンテキストマネージャ。
    
    autoreleasepool 内で処理を行い、抜ける際に少しだけ NSRunLoop を回して
    ペンディング中の Mach port メッセージをフラッシュさせる。
    """
    try:
        import objc
        from Foundation import NSRunLoop, NSDate
    except ImportError:
        # macOS 以外、または PyObjC がない環境では何もしない
        yield
        return

    with objc.autorelease_pool():
        yield
        # 処理完了後、現在のスレッドの RunLoop をごくわずかな時間(0.001秒)だけ回し、
        # 溜まっている Mach メッセージをディスパッチさせる
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.001))
