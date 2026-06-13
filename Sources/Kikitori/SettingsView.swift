import SwiftUI
import KikitoriCore

// MARK: - ViewModel

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var language: String = "ja"
    @Published var uiLanguage: String = "ja"
    @Published var hotkeyFn: Bool = false
    @Published var hotkeyCtrl: Bool = false
    @Published var hotkeyAlt: Bool = false
    @Published var hotkeyCmd: Bool = false
    @Published var hotkeyShift: Bool = false
    @Published var minDurationMs: Double = 300
    @Published var maxDurationSec: Double = 60
    @Published var silenceRmsThreshold: Double = 0.0001
    @Published var debugEnabled: Bool = false
    @Published var glossaryText: String = ""

    private let settings: SettingsManager

    init(settings: SettingsManager) {
        self.settings = settings
    }

    func load() {
        language = settings.language
        uiLanguage = settings.uiLanguage ?? "ja"
        loadHotkeyToggles()
        minDurationMs = Double(settings.minDurationMs)
        maxDurationSec = Double(settings.maxDurationSec)
        silenceRmsThreshold = settings.silenceRmsThreshold
        debugEnabled = settings.debug
        glossaryText = settings.glossary.joined(separator: "\n")
    }

    private func loadHotkeyToggles() {
        hotkeyFn = false; hotkeyCtrl = false; hotkeyAlt = false
        hotkeyCmd = false; hotkeyShift = false
        for name in settings.hotkey {
            switch name.lowercased() {
            case "fn":    hotkeyFn = true
            case "ctrl":  hotkeyCtrl = true
            case "alt", "option": hotkeyAlt = true
            case "cmd":   hotkeyCmd = true
            case "shift": hotkeyShift = true
            default: break
            }
        }
    }

    func save() {
        settings.language = language
        settings.uiLanguage = uiLanguage
        settings.hotkey = hotkeyArray
        settings.minDurationMs = Int(minDurationMs)
        settings.maxDurationSec = Int(maxDurationSec)
        settings.silenceRmsThreshold = silenceRmsThreshold
        settings.debug = debugEnabled
        // 用語リスト: 1行1用語 → 空行除去 → 配列
        settings.glossary = glossaryText
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        settings.save()
    }

    private var hotkeyArray: [String] {
        var keys: [String] = []
        if hotkeyFn { keys.append("fn") }
        if hotkeyCtrl { keys.append("ctrl") }
        if hotkeyAlt { keys.append("option") }
        if hotkeyCmd { keys.append("cmd") }
        if hotkeyShift { keys.append("shift") }
        return keys.isEmpty ? ["fn"] : keys
    }

    func reset() {
        settings.reset()
        load()
        glossaryText = ""
    }

    /// 認識言語の選択肢
    var languageOptions: [(String, String)] {
        [
            ("ja", "日本語"),
            ("en", "English"),
            ("zh", "中文"),
            ("ko", "한국어"),
            ("fr", "Français"),
            ("de", "Deutsch"),
        ]
    }
}

// MARK: - View

struct SettingsView: View {
    @ObservedObject var vm: SettingsViewModel
    let onSave: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            TabView {
                generalTab
                    .tabItem { Label("一般", systemImage: "gearshape") }
                    .padding(20)
                filtersTab
                    .tabItem { Label("フィルタ", systemImage: "waveform") }
                    .padding(20)
            }
            Divider()
            HStack {
                Spacer()
                Button("保存") {
                    vm.save()
                    onSave()
                }
                .keyboardShortcut(.defaultAction)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 10)
        }
        .frame(width: 420, height: 350)
    }

    private var generalTab: some View {
        Form {
            Picker("認識言語:", selection: $vm.language) {
                ForEach(vm.languageOptions, id: \.0) { code, label in
                    Text(label).tag(code)
                }
            }

            Picker("UI 表示言語:", selection: $vm.uiLanguage) {
                Text("日本語").tag("ja")
                Text("English").tag("en")
            }

            Text("ホットキー（修飾キーの組み合わせ）:")
                .font(.subheadline)
            
            Toggle("Fn      🌐", isOn: $vm.hotkeyFn)
            Toggle("Control ⌃", isOn: $vm.hotkeyCtrl)
            Toggle("Option  ⌥", isOn: $vm.hotkeyAlt)
            Toggle("Command ⌘", isOn: $vm.hotkeyCmd)
            Toggle("Shift    ⇧", isOn: $vm.hotkeyShift)

            HStack {
                Spacer()
                Button("デフォルトに戻す") { vm.reset() }
            }

            Divider()

            VStack(alignment: .leading, spacing: 4) {
                Text("認識精度向上用語（1行1用語）:")
                    .font(.subheadline)
                TextEditor(text: $vm.glossaryText)
                    .font(.system(size: 12, design: .monospaced))
                    .frame(height: 60)
                    .border(.secondary.opacity(0.3))
            }
        }
    }

    private var filtersTab: some View {
        Form {
            HStack {
                Text("最低録音時間:")
                Slider(value: $vm.minDurationMs, in: 100...5000, step: 100)
                Text("\(Int(vm.minDurationMs))ms")
                    .frame(width: 60, alignment: .trailing)
            }

            HStack {
                Text("最大録音時間:")
                Slider(value: $vm.maxDurationSec, in: 10...300, step: 10)
                Text("\(Int(vm.maxDurationSec))秒")
                    .frame(width: 60, alignment: .trailing)
            }

            HStack {
                Text("無音判定 RMS:")
                Slider(value: $vm.silenceRmsThreshold, in: 0...0.01, step: 0.0001)
                Text(String(format: "%.4f", vm.silenceRmsThreshold))
                    .frame(width: 60, alignment: .trailing)
            }

            Toggle("デバッグログ", isOn: $vm.debugEnabled)
        }
    }
}

// MARK: - Window Controller

final class SettingsWindowController: NSWindowController {
    private let vm: SettingsViewModel

    init(settings: SettingsManager, onSave: @escaping () -> Void) {
        self.vm = SettingsViewModel(settings: settings)
        vm.load()

        let window = NSWindow(
            contentRect: .zero,
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: true
        )
        window.title = "Kikitori 設定"
        window.setContentSize(NSSize(width: 420, height: 350))
        window.center()
        window.isReleasedWhenClosed = false

        super.init(window: window)

        let view = SettingsView(vm: vm, onSave: { [weak self] in
            onSave()
        })
        window.contentViewController = NSHostingController(rootView: view)
    }

    required init?(coder: NSCoder) { fatalError() }

    func show() {
        vm.load()
        window?.center()
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}
