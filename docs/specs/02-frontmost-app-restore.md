# 02 — Frontmost App Tracker

## 目的
ホットキーを押した瞬間の最前面アプリを記憶し、ペースト完了後にそのアプリを再アクティブにする。ホットキー監視中にフォーカスがアプリから逸れるのを防ぐ。

## Python 版参照
`kikitori/settings.py`:
```python
def get_frontmost_pid() -> int | None:
    from AppKit import NSWorkspace
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return int(app.processIdentifier())

def activate_app_by_pid(pid: int) -> bool:
    from AppKit import NSRunningApplication
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    app.activateWithOptions_(NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps)
```

`kikitori/hotkey_manager.py` の `on_press()`:
```python
self._target_pid = get_frontmost_pid()  # 録音開始時
```

`on_release()`:
```python
# アプリ切替はバックグラウンドスレッドで（blocking AppKit 呼び出しを回避）
threading.Thread(target=lambda: activate_app_by_pid(target_pid), daemon=True).start()
```

## Swift 実装仕様

### インターフェース
```swift
public final class FrontmostAppTracker: Sendable {
    public init() {}
    public func capture() -> pid_t?       // 現在の最前面 PID を記憶
    public func restore(pid: pid_t?)      // PID のアプリをアクティブ化
}
```

### 実装詳細
1. **capture()**:
   ```swift
   let app = NSWorkspace.shared.frontmostApplication
   return app?.processIdentifier
   ```
   - 録音開始時（`onKeyDown` → `startRecording()`）に呼ぶ
   - 返り値の pid は AppDelegate が保持

2. **restore(pid:)**:
   ```swift
   guard let pid else { return }
   guard let app = NSRunningApplication(processIdentifier: pid) else { return }
   app.activate(options: [.activateAllWindows, .activateIgnoringOtherApps])
   ```
   - ペースト後（`inject()` 後）に呼ぶ
   - Python 版と同様、バックグラウンドスレッドで実行（`Task.detached` 使用）
   - アクティベーションには Accessibility 権限が必要

3. **呼び出しタイミング**（AppDelegate 修正）:
   ```swift
   private func startRecording() {
       let pid = tracker.capture()
       // ... 録音開始 ...
   }
   
   private func stopRecording() {
       // ... 認識・ペースト ...
       Task.detached { [weak self] in
           self?.tracker.restore(pid: pid)  // 保持しておいた pid
       }
   }
   ```

### 単体テスト
- `capture()` が pid_t を返すこと
- `restore(nil)` がクラッシュしないこと
- 存在しない PID で `restore()` が安全に失敗すること
