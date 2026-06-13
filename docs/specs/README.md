# Kikitori 仕様書一覧

## 実装済みコアパイプライン（Swift）

| コンポーネント | ファイル | 役割 |
|-------------|---------|------|
| AudioCapture | `Sources/KikitoriCore/AudioCapture.swift` | 専用シリアルキュー上の AVAudioEngine。マイク入力 → 必要に応じて AVAudioConverter でリサンプル → コールバック |
| SpeechRecognizer | `Sources/KikitoriCore/SpeechRecognizer.swift` | SpeechAnalyzer + SpeechTranscriber（macOS 26.0 の新 API）。BufferQueue にバッファを貯め、録音終了時に AsyncStream<AnalyzerInput> で analyzeSequence → finalizeAndFinishThroughEndOfInput → results 収集 |
| HotkeyManager | `Sources/KikitoriCore/HotkeyManager.swift` | NSEvent.addGlobalMonitorForEvents（.flagsChanged）。Option キー押下/解放を NSLock でスレッドセーフに検知 |
| TextInjector | `Sources/KikitoriCore/TextInjector.swift` | NSPasteboard.general にコピー → CGEvent で Cmd+V（virtualKey 0x09）を .cghidEventTap にポスト |
| AppDelegate | `Sources/Kikitori/AppDelegate.swift` | NSMenu メニューバー。onKeyDown → startRecording（Task { } で @MainActor をブロックせず）、onKeyUp → stopRecording → inject |
| main | `Sources/Kikitori/main.swift` | NSApplication.accessory で起動 |

### アーキテクチャ上の重要判断
- **AVAudioEngine は専用シリアルキューで実行**: メインアクターをブロックしない（エンジン起動に ~100ms かかるため）
- **AudioCapture.start() は async throws**: `withCheckedThrowingContinuation` + `queue.async` で非同期化
- **全クラスは @unchecked Sendable**: Swift 6 の厳密並行性チェックに対応（NSLock、AVAudioEngine 等の内部可変状態を自前で保護）
- **NSLock.withLock {}**: async コンテキストからの lock()/unlock() 禁止に対応
- **SwiftUI 非依存**: 空白ウィンドウ問題を回避。純粋 AppKit

---

## 実装予定機能

| # | 仕様 | 優先度 | Python 版参照 |
|---|------|--------|-------------|
| 02 | Frontmost App Tracker | 高 | `settings.py:get_frontmost_pid()` |
| 03 | IME 自動切替 | 中 | `input_source.py` |
| 04 | Min Duration Filter | 高 | `hotkey_manager.py:_should_transcribe()` |
| 05 | Max Duration AutoStop | 高 | `hotkey_manager.py:_start_auto_stop_timer()` |
| 06 | Silence RMS Filter | 高 | `hotkey_manager.py:_should_transcribe()` |
| 07 | Custom Hotkey | 高 | `hotkey_manager.py:resolve_hotkey()` |
| 08 | Settings File | 高 | `settings.py`, `config.py` |
| 09 | Settings GUI | 中 | `settings_dialog.py` |
| 10 | Glossary | 低 | `glossary.py`, `glossary_dialog.py` |
| 11 | Corrections | 低 | `corrections.py`, `corrections_dialog.py` |
| 12 | i18n | 中 | `i18n.py` |
| 13 | Waveform Overlay | 中 | `overlay.py`, `audio_buffer.py:get_recent_amplitudes()` |
| 15 | Debug Mode | 低 | `config.py:DEBUG/BENCHMARK_MODE` |
| 16 | Homebrew Formula | 高 | `Formula/kikitori.rb` |

> #01, #03, #14 は欠番（#01=未定義、#03=IME切替は開発中検討、#14=未定義）
