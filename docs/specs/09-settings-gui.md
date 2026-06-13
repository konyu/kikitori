# 09 — Settings GUI

## 目的
設定ファイルを直接編集せずに、GUI から全設定を変更可能にする。

## Python 版参照
`kikitori/settings_dialog.py`（PySide6 QDialog）:
- 認識言語: QComboBox（ja, en, zh, ko, fr, de, it, es, pt, ru, nl, pl, tr, ar, hi, th, vi）
- UI 言語: QComboBox（ja, en）
- ホットキー: 修飾キー QCheckBox × 4（Ctrl, Option/Alt, Cmd, Shift）+ 追加キー QComboBox（無し, a-z, 0-9, F1-F20, Space, Tab, Escape）
- 最低録音時間: QSpinBox（100-5000ms, step=100）
- デフォルトに戻す: QPushButton
- 保存して適用: QPushButton + キャンセル: QPushButton
- レイアウト: QFormLayout + QDialogButtonBox

## Swift 実装仕様

### SettingsView（SwiftUI）
```swift
struct SettingsView: View {
    @ObservedObject var viewModel: SettingsViewModel
    
    var body: some View {
        Form {
            // 認識言語
            Picker("認識言語", selection: $viewModel.language) {
                Text("日本語").tag("ja")
                Text("English").tag("en")
                // ...
            }
            
            // UI 言語
            Picker("UI 言語", selection: $viewModel.uiLanguage) {
                Text("日本語").tag("ja")
                Text("English").tag("en")
            }
            
            // ホットキー
            Section("ホットキー") {
                // 修飾キー選択
                // カスタムキー選択
            }
            
            // フィルタ設定
            Section("フィルタ") {
                Stepper("最低録音時間: \(viewModel.minDurationMs, specifier: "%.0f")ms",
                        value: $viewModel.minDurationMs, in: 100...5000, step: 100)
                Stepper("最大録音時間: \(viewModel.maxDurationSec, specifier: "%.0f")秒",
                        value: $viewModel.maxDurationSec, in: 10...300, step: 10)
            }
            
            // デバッグモード
            Toggle("デバッグログ", isOn: $viewModel.debug)
        }
        .padding()
        .frame(width: 400, height: 350)
    }
}
```

### SettingsViewModel（ObservableObject）
```swift
@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var language: String
    @Published var uiLanguage: String
    @Published var hotkeyModifiers: [HotkeyModifier]
    @Published var hotkeyKey: HotkeyKey?
    @Published var minDurationMs: Double
    @Published var maxDurationSec: Double
    @Published var debug: Bool
    
    private let settings: SettingsManager
    private let onApply: () -> Void  // 設定反映コールバック
    
    func load()   // SettingsManager から読み込み
    func save()   // SettingsManager に保存 + onApply()
    func reset()  // デフォルトに戻す
}
```

### SettingsWindowController（NSWindowController）
```swift
final class SettingsWindowController: NSWindowController {
    // NSHostingController(rootView: SettingsView(...)) を contentViewController に設定
    // ウィンドウを close 時に破棄せず隠すだけ（再表示で状態維持）
    func show()  // makeKeyAndOrderFront
}
```

### 起動方法
- メニューバー「設定」→ `showSettings()`
- または Cmd+, ショートカット（`keyEquivalent: ","`）

### 注意点
- **SwiftUI 依存**: この機能だけが SwiftUI を必要とする。SwiftUI.framework がリンクされるため、空白ウィンドウ対策が必要
- 空白ウィンドウ対策: `NSApp.setActivationPolicy(.accessory)` を最速で実行（main.swift の `import` より前）、または `@main App` プロトコルで明示的に制御
- i18n 対応後は全ラベルを `I18n.t(.settingsTitle)` 等で切り替え

### 単体テスト
- load() で SettingsManager の値が反映される
- save() で SettingsManager に値が書き込まれる
- reset() でデフォルト値に戻る
