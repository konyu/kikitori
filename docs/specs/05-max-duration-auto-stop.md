# 05 — Max Duration AutoStop

## 目的
長時間録音によるメモリ枯渇を防ぐ。最大時間を超えたら自動停止し、既存バッファで認識を実行する。

## Python 版参照
`kikitori/config.py`:
```python
MAX_DURATION: float = 60.0  # 秒
```

`kikitori/hotkey_manager.py:_start_auto_stop_timer()`:
```python
def _start_auto_stop_timer(self):
    self._cancel_auto_stop_timer()
    self._timer = threading.Timer(self._max_duration, self._on_auto_stop)
    self._timer.start()

def _on_auto_stop(self):
    with self._lock:
        if not self._is_recording:
            return
        self._is_recording = False
    audio = self._recorder.stop()
    if self._should_transcribe(audio):
        self._transcribe_and_inject(audio)
    # キーがまだ押されていれば再録音
    with self._lock:
        if self._all_hotkey_pressed():
            self._is_recording = True
            self._recorder.start()
            self._start_auto_stop_timer()
```

### Python 版の重要な挙動
- **再録音**: 最大時間で停止後、まだホットキーが押されていれば自動的に新しい録音を開始する
- **タイマーは `threading.Timer`**: 別スレッドで実行され、メインスレッドをブロックしない

## Swift 実装仕様

### AppDelegate に追加
```swift
private var maxDurationSec: Double = 60.0
private var autoStopTask: Task<Void, Never>?

private func startRecording() {
    // ...
    // 自動停止タスクを開始
    autoStopTask = Task {
        try? await Task.sleep(nanoseconds: UInt64(maxDurationSec * 1_000_000_000))
        await MainActor.run { [weak self] in
            self?.handleAutoStop()
        }
    }
}

private func handleAutoStop() {
    guard isRecording else { return }
    // 現在の録音を停止・処理
    stopRecording()
    // キーがまだ押されていれば再録音
    if hotkeyManager.isHotkeyDown {
        startRecording()
    }
}
```

### HotkeyManager に追加
```swift
public var isHotkeyDown: Bool {
    lock.withLock { down }
}
```

### 設定ファイル
```yaml
max_duration_sec: 60
```

### 注意点
- `Task.sleep` はキャンセル可能。録音が手動停止されたら `autoStopTask?.cancel()` する
- 再録音時は新しい SpeechRecognizer インスタンスを作成する（前回の認識器は破棄済み）

### 単体テスト
- 60 秒経過で自動停止
- 自動停止後、キー押下中なら再録音
- 手動停止でタイマーがキャンセルされる
