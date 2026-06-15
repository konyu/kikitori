# 15 — Debug Mode（デバッグモード）

## 目的
開発者・トラブルシューティング用の詳細ログ出力。Console.app で確認可能。

## Python 版参照
`kikitori/config.py`:
```python
DEBUG: bool = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")
BENCHMARK_MODE: bool = os.environ.get("BENCHMARK_MODE", "").lower() in ("true", "1", "yes")
```

`kikitori/hotkey_manager.py`:
```python
if DEBUG: print(f"[DEBUG] _should_transcribe: audio.size={audio.size} ...")
if BENCHMARK_MODE: print(f"[BENCH] pipeline: transcribe={...}ms inject={...}ms total={...}ms")
```

### Python 版のログ出力箇所
- `_should_transcribe()`: 録音サイズ、RMS 値、判定結果
- `_transcribe_and_inject()`: 認識テキスト長、校正後テキスト、注入呼び出し
- `recorder.start()`: PortAudio 起動時間
- `recorder.stop()`: 停止時間
- `inject()`: 注入前テキスト、クリップボード操作

## Swift 実装仕様

### 設定
```yaml
debug: false  # 設定ファイル
# または環境変数 DEBUG=true でも有効化（Python 版互換）
```

### DebugLogger クラス
```swift
public final class DebugLogger: Sendable {
    public var isEnabled: Bool
    
    public init(enabled: Bool = false)
    
    public func debug(_ category: String, _ message: String) {
        guard isEnabled else { return }
        NSLog("[Kikitori][DEBUG][%@] %@", category, message)
    }
    
    public func error(_ category: String, _ message: String) {
        // エラーは常に出力
        NSLog("[Kikitori][ERROR][%@] %@", category, message)
    }
}
```

### 依存注入
全コンポーネントが `DebugLogger` を受け取れるようにする:
```swift
public class AudioCapture {
    public var debugLog: DebugLogger?
    // ...
    private func deliverBuffer(...) {
        debugLog?.debug("Audio", "Buffer: \(buffer.frameLength) frames")
    }
}
```

### ログカテゴリ
| カテゴリ | 対象 |
|---------|------|
| Audio | AudioCapture: バッファ数、コンバーター成否 |
| Speech | SpeechRecognizer: 初期化、フレーム数、フィルタ判定、認識結果 |
| Hotkey | HotkeyManager: キー押下/解放、フラグ状態 |
| Inject | TextInjector: テキスト長、Cmd+V 実行 |
| App | AppDelegate: 録音開始/停止、認識結果、エラー |

### 環境変数
```bash
DEBUG=true swift run  # デバッグログ有効化
```

### ベンチマークモード
```yaml
benchmark: false  # 各段階のレイテンシ計測
# AudioCapture.start → Nms
# SpeechRecognizer.start → Nms
# analyzeSequence → Nms
# total pipeline → Nms
```

### 単体テスト
- デフォルトで無効
- 設定ファイルで有効化
- 環境変数で有効化
- debug() は無効時呼ばれてもクラッシュしない
