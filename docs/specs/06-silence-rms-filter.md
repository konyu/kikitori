# 06 — Silence RMS Filter

## 目的
無音状態の録音（マイクミュート、無入力等）をフィルタし、空の認識結果を貼り付けない。

## Python 版参照
`kikitori/config.py`:
```python
SILENCE_RMS_THRESHOLD: float = 0.0001
```

`kikitori/hotkey_manager.py:_should_transcribe()`:
```python
if self._silence_rms_threshold > 0:
    import numpy as np
    rms = float(np.sqrt(np.dot(audio, audio) / audio.size))
    if rms < self._silence_rms_threshold:
        print(f"無音と判定されました（RMS={rms:.4f} < {threshold}）")
        return False
```

### 計算式
```
RMS = sqrt(sum(sample^2 for sample in audio) / audio.size)
```
- NumPy: `np.sqrt(np.dot(audio, audio) / audio.size)`
- 実効値（Root Mean Square）
- 閾値以下 = 無音判定

## Swift 実装仕様

### SpeechRecognizer に追加
```swift
public var silenceRmsThreshold: Float = 0.0001

public func stop() async -> String {
    // ... min duration チェック後 ...
    
    if silenceRmsThreshold > 0 {
        let rms = calculateRMS()
        if rms < silenceRmsThreshold {
            return ""
        }
    }
    // ... 認識処理 ...
}

private func calculateRMS() -> Float {
    // bufferQueue 内の全フレームの RMS を計算
    // RMS = sqrt(mean(sample^2))
    var sumSq: Float = 0
    let count = totalFrameCount
    guard count > 0 else { return 0 }
    // BufferQueue から逐次読み出し
    // 注: バッファは再利用されるため、コピーして計算
    return sqrt(sumSq / Float(count))
}
```

### 実装上の注意
- BufferQueue のバッファは `AVAudioPCMBuffer`（Int16 サンプル）。RMS 計算前に Float32 に変換
- `AVAudioPCMBuffer.floatChannelData` または手動変換を使用
- バッファが大量の場合のメモリ使用に注意（最大 60 秒 × 16000 Hz = 960,000 サンプル、Float32 で ~3.8MB）

### 設定ファイル
```yaml
silence_rms_threshold: 0.0001  # 0 にすると無効化
```

### 単体テスト
- 無音バッファ（全ゼロ）で空文字
- RMS = 閾値ちょうどで通過
- RMS < 閾値で空文字
