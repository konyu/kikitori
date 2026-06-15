# 03 — IME 自動切替

## 目的
録音開始時に自動的に ASCII 入力モードに切り替え（ホットキー押下で全角文字が入力されるのを防ぐ）、ペースト後に元の日本語 IME 状態に復元する。

## Python 版参照
`kikitori/input_source.py`:
```python
def save_and_switch_to_ascii() -> bool:
    """現在の入力ソースが日本語IMEならASCIIに切り替えてTrueを返す"""
    from Carbon import TISCopyCurrentKeyboardInputSource
    source = TISCopyCurrentKeyboardInputSource()
    source_id = TISGetInputSourceProperty(source, kTISPropertyInputSourceID)
    # "com.apple.inputmethod.Kotoeri.Japanese" 等をチェック
    # 日本語なら ASCII に切り替え

def restore_to_kana() -> None:
    """元の日本語IME入力ソースに復元"""
```

## Swift 実装仕様

### InputSourceManager クラス
```swift
public final class InputSourceManager: Sendable {
    public func saveAndSwitchToASCII() -> Bool
    public func restoreToKana()
}
```

### 実装詳細
1. **saveAndSwitchToASCII()**:
   - `TISCopyCurrentKeyboardInputSource()` で現在の入力ソース取得
   - `TISGetInputSourceProperty(source, kTISPropertyInputSourceID)` で source ID 取得
   - 日本語 IME（`com.apple.inputmethod.Kotoeri.*`）なら ASCII（`com.apple.keylayout.US`）に `TISSelectInputSource()` で切り替え
   - 日本語だった場合 `true` を返す（復元必要のフラグ）

2. **restoreToKana()**:
   - `TISSelectInputSource()` で元の日本語入力ソースに戻す
   - バックグラウンドスレッドで実行（ペースト後の IME 復元）

3. **呼び出しタイミング**:
   - `startRecording()`: `let needsRestore = inputSource.saveAndSwitchToASCII()`
   - `inject()` 完了後: `if needsRestore { inputSource.restoreToKana() }`

### 注意点
- Carbon framework の Text Input Source Services API は非推奨だが、代替 API なし
- macOS 26.0 でも動作確認必要
- IDE 実行時は SIGABRT の可能性あり → ターミナル直接実行推奨
