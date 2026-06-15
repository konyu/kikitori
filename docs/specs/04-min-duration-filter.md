# 04 — Min Duration Filter

## 目的
極短い録音（ホットキーの誤タップ等）をフィルタし、無意味な認識処理を回避する。

## Python 版参照
`kikitori/config.py`:
```python
MIN_DURATION_MS: float = 300.0  # ミリ秒
```

`kikitori/hotkey_manager.py:_should_transcribe()`:
```python
def _should_transcribe(self, audio) -> bool:
    if audio.size == 0:
        return False
    if audio.size < self._min_duration_samples:
        # self._min_duration_samples = int(min_duration_ms / 1000 * SAMPLE_RATE)
        duration_ms = audio.size / SAMPLE_RATE * 1000
        print(f"録音が短すぎます（{duration_ms:.0f}ms < {min_ms:.0f}ms）")
        return False
```

## Swift 実装仕様

### SpeechRecognizer に追加
```swift
public var minDurationMs: Int = 300  // デフォルト 300ms

public func stop() async -> String {
    // ...
    // フィルタチェック（analyzeSequence 前に判定）
    if minDurationMs > 0 {
        let minFrames = AVAudioFrameCount(Float(minDurationMs) * sampleRate / 1000)
        if totalFrameCount < minFrames {
            return ""
        }
    }
    // ... 認識処理 ...
}
```

### 判定式
```
minFrames = minDurationMs × sampleRate / 1000
```
- `sampleRate = 16000`
- `minDurationMs = 300` → `minFrames = 4800`
- `totalFrameCount < 4800` なら空文字を返す

### 設定ファイル連携
`~/.kikitori_settings.yaml`:
```yaml
min_duration_ms: 300
```

### 単体テスト
- 0 フレームで空文字
- `minDurationMs - 1` フレームで空文字
- `minDurationMs` フレームで認識処理実行
