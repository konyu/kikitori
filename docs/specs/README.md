# Kikitori 仕様書一覧

## 実装済みコアパイプライン（Swift）

| コンポーネント | ファイル | 役割 |
|-------------|---------|------|
| AudioCapture | `Sources/KikitoriCore/AudioCapture.swift` | 専用シリアルキュー上の AVAudioEngine。マイク入力 → 必要に応じて AVAudioConverter でリサンプル → コールバック |
| SpeechRecognizer | `Sources/KikitoriCore/SpeechRecognizer.swift` | SpeechAnalyzer + SpeechTranscriber（macOS 26.0 API）。BufferQueue → AsyncStream<AnalyzerInput> → analyzeSequence → finalizeAndFinishThroughEndOfInput → results 収集 |
| HotkeyManager | `Sources/KikitoriCore/HotkeyManager.swift` | NSEvent.addGlobalMonitorForEvents（.flagsChanged）。Option キー押下/解放を NSLock でスレッドセーフに検知 |
| TextInjector | `Sources/KikitoriCore/TextInjector.swift` | NSPasteboard.general にコピー → CGEvent で Cmd+V（virtualKey 0x09）を .cghidEventTap にポスト |
| AppDelegate | `Sources/Kikitori/AppDelegate.swift` | NSMenu メニューバー。onKeyDown → startRecording（Task {} で @MainActor をブロックせず）、onKeyUp → stopRecording → inject |
| main | `Sources/Kikitori/main.swift` | NSApplication.accessory で起動 |

### アーキテクチャ上の重要判断
- **AVAudioEngine は専用シリアルキューで実行**: メインアクターをブロックしない（エンジン起動に ~100ms かかるため）
- **AudioCapture.start() は async throws**: `withCheckedThrowingContinuation` + `queue.async` で非同期化
- **全クラスは @unchecked Sendable**: Swift 6 の厳密並行性チェックに対応
- **NSLock.withLock {}**: async コンテキストからの lock()/unlock() 禁止に対応

---

## 実装順序

### Phase 1: Foundation（基盤）— 最初に固める
| # | 仕様 | 理由 |
|---|------|------|
| **08** | Settings File | 全機能の設定を永続化する基盤。他機能の多くが依存。 |
| **12** | i18n | GUI/ログの日本語/英語切替。早期に入れておかないと後で文字列の修正漏れが起きる。 |

### Phase 2: Core Improvements（録音・認識パイプライン強化）
| # | 仕様 | 理由 |
|---|------|------|
| **04** | Min Duration Filter | 誤タップ防止。実装が単純で効果大。 |
| **06** | Silence RMS Filter | 無音フィルタ。RMS 計算は AudioCapture に追加するだけ。 |
| **02** | Frontmost App Tracker | ペースト後のアプリ復帰。独立していて依存少。 |
| **11** | Corrections | 認識テキストの後処理置換。独立コンポーネント。 |
| **05** | Max Duration AutoStop | 長時間録音の自動停止＋再録音。やや複雑（タイマー＋状態管理）。 |

### Phase 3: UX / Polish
| # | 仕様 | 理由 |
|---|------|------|
| **07** | Custom Hotkey | #08 に依存。Option 以外のキーを使いたいユーザー向け。 |
| **09** | Settings GUI | #08 + #12 + #07 に依存。SwiftUI ウィンドウ。 |
| **13** | Waveform Overlay | 録音中フィードバック。SwiftUI 依存だが単独で実装可。 |

### Phase 4: Deployment / Tooling
| # | 仕様 | 理由 |
|---|------|------|
| **16** | Homebrew Formula | `brew install` 配布。リリース準備時に。 |
| **15** | Debug Mode | 開発者ツール。NSLog ラッパー。 |
| **10** | Glossary | Apple Speech API に contextualStrings 相当があるか要確認。不確実なので最後。 |

### Pending（ペンディング）
| # | 仕様 | 理由 |
|---|------|------|
| **03** | IME Auto Switch | Carbon TIS API が macOS 26.0 で動作するか要検証。録音開始時に ASCII 切替 + ペースト後復元。IDE 実行で SIGABRT リスク。 |

> #01, #14 は欠番

---

## 依存グラフ
```
           ┌──────────────────────────┐
           │      08 Settings File     │ ← Phase 1
           └────────┬─────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
  04 MinDur    06 Silence    07 CustomHotkey (Phase 3)
  (Phase 2)    (Phase 2)          │
                    │              ▼
                    │       09 Settings GUI (Phase 3)
                    │
  12 i18n ← Phase 1（独立）
  02 Frontmost ← Phase 2（独立）
  11 Corrections ← Phase 2（独立）
  05 MaxDuration ← Phase 2（独立）
  13 Overlay ← Phase 3（独立）
  16 Formula ← Phase 4（独立）
  15 Debug ← Phase 4（独立）
  10 Glossary ← Phase 4（API要確認）
```
