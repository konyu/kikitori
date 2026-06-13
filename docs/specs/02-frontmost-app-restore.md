# Frontmost App Tracker

録音開始時に最前面アプリケーションの PID を記憶し、ペースト後にそのアプリを再度アクティブにする。

## 要件
- `NSWorkspace.shared.frontmostApplication?.processIdentifier` で PID 取得
- 録音開始時（`onKeyDown`）に `capture()`
- ペースト後（`inject()` 後）に `restore()`
- `NSRunningApplication(processIdentifier:)` + `activate()` で復元
