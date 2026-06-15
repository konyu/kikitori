# 13 — Waveform Overlay（波形オーバーレイ）

## 目的
録音中に画面上に半透明の波形アニメーションを表示し、録音状態を視覚的にフィードバックする。

## Python 版参照
`kikitori/overlay.py`（PySide6 QWidget）:
- フレームレス、最前面、フォーカス拒否、マウス透過、半透明背景
- 12 本の縦バー波形 + 青いマイクインジケーター
- 30fps タイマーでアニメーション更新
- Aqua Voice 風カプセル型ピルデザイン（170×44px）
- 画面中央下に配置

`kikitori/audio_buffer.py:get_recent_amplitudes()`:
```python
def get_recent_amplitudes(self, n_bars=30, window_ms=50.0):
    # 直近の音声振幅を n_bars 個分取得
    # 各バー: window_ms 分のサンプルの最大絶対値 × 4（正規化）
```

## Swift 実装仕様

### OverlayController クラス
```swift
public final class OverlayController: @unchecked Sendable {
    private var window: NSWindow?
    private let lock = NSLock()
    
    public init() {}
    public func show()             // オーバーレイ表示
    public func hide()             // 非表示
    public func updateAmplitudes(_ amplitudes: [Float])  // 波形データ更新
}
```

### ウィンドウ設定
```swift
private func createWindow() -> NSWindow {
    let window = NSWindow(
        contentRect: NSRect(x: 0, y: 0, width: 170, height: 44),
        styleMask: [.borderless],
        backing: .buffered,
        defer: false
    )
    window.level = .floating
    window.isOpaque = false
    window.backgroundColor = .clear
    window.ignoresMouseEvents = true
    window.collectionBehavior = [.canJoinAllSpaces, .stationary]
    window.hasShadow = false
    
    // 画面中央下に配置
    if let screen = NSScreen.main {
        let screenRect = screen.visibleFrame
        let x = screenRect.midX - 85
        let y = screenRect.minY + 28
        window.setFrameOrigin(NSPoint(x: x, y: y))
    }
    
    // SwiftUI オーバーレイビューをホスト
    let hosting = NSHostingController(rootView: OverlayWaveformView())
    window.contentViewController = hosting
    
    return window
}
```

### OverlayWaveformView（SwiftUI）
```swift
struct OverlayWaveformView: View {
    @State var amplitudes: [Float] = Array(repeating: 0, count: 12)
    @State var phase: Double = 0
    let timer = Timer.publish(every: 1/30, on: .main, in: .common).autoconnect()
    
    var body: some View {
        ZStack {
            // カプセル型背景（グラデーション）
            RoundedRectangle(cornerRadius: 22)
                .fill(LinearGradient(...))
            
            HStack(spacing: 0) {
                // 青いマイクインジケーター
                Circle()
                    .fill(RadialGradient(...))
                    .frame(width: 14, height: 14)
                    .padding(.leading, 16)
                
                Spacer().frame(width: 10)
                
                // 12本の波形バー
                ForEach(0..<12, id: \.self) { i in
                    WaveformBar(amplitude: amplitudes[i], isActive: maxAmplitude > 0.05)
                }
                
                Spacer().frame(width: 30)
            }
        }
        .frame(width: 170, height: 44)
    }
}
```

### 波形更新パイプライン
1. `AudioCapture.onAudioBuffer` → `SpeechRecognizer.addAudio(buffer)` → 現状の録音バッファから振幅を計算
2. `AudioCapture` に振幅計算コールバックを追加（`onAmplitudeUpdate: (([Float]) -> Void)?`）
3. コールバックが `OverlayController.updateAmplitudes()` を呼ぶ

### 振幅計算（Python 版互換）
```swift
// AudioCapture 内で定期的に計算（例: 10 バッファごと）
private var sampleBuffer: [Float] = []
private var bufferCount = 0

func calculateAmplitudes(nBars: Int = 12, windowMs: Float = 50.0) -> [Float] {
    // 直近のサンプルから振幅を計算
    // Python 版と同様のロジック
}
```

### 注意点
- **SwiftUI 依存**: この機能が SwiftUI を必要とする
- オーバーレイが不要な場合（設定で無効化可能にするのが望ましい）
- パフォーマンス: 30fps アニメーション + 波形計算は軽量であるべき

### 単体テスト
- show/hide でウィンドウの表示/非表示
- 振幅データの更新がクラッシュしない
- 0 振幅でアイドルアニメーション
