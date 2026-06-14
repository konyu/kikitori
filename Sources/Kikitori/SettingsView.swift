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
    @ObservedObject var i18n: I18n
    let onSave: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            TabView {
                generalTab
                    .tabItem { Label(i18n.t(.tabGeneral), systemImage: "gearshape") }
                    .padding(20)
                filtersTab
                    .tabItem { Label(i18n.t(.tabFilters), systemImage: "waveform") }
                    .padding(20)
            }
            Divider()
            HStack {
                Spacer()
                Button(i18n.t(.settingsSaveBtn)) {
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
            Picker(i18n.t(.settingsLanguageLabel), selection: $vm.language) {
                ForEach(vm.languageOptions, id: \.0) { code, label in
                    Text(label).tag(code)
                }
            }

            Picker(i18n.t(.settingsUILanguageLabel), selection: $vm.uiLanguage) {
                Text("日本語").tag("ja")
                Text("English").tag("en")
            }

            Text(i18n.t(.settingsHotkeyLabel))
                .font(.subheadline)
            
            Toggle("Fn      🌐", isOn: $vm.hotkeyFn)
            Toggle("Control ⌃", isOn: $vm.hotkeyCtrl)
            Toggle("Option  ⌥", isOn: $vm.hotkeyAlt)
            Toggle("Command ⌘", isOn: $vm.hotkeyCmd)
            Toggle("Shift    ⇧", isOn: $vm.hotkeyShift)

            HStack {
                Spacer()
                Button(i18n.t(.settingsResetBtn)) { vm.reset() }
            }
        }
    }

    private var filtersTab: some View {
        Form {
            HStack {
                Text(i18n.t(.settingsMinDurLabel))
                Slider(value: $vm.minDurationMs, in: 100...5000, step: 100)
                Text("\(Int(vm.minDurationMs))\(i18n.t(.msUnit))")
                    .frame(width: 60, alignment: .trailing)
            }

            HStack {
                Text(i18n.t(.settingsMaxDurLabel))
                Slider(value: $vm.maxDurationSec, in: 10...300, step: 10)
                Text("\(Int(vm.maxDurationSec))\(i18n.t(.secUnit))")
                    .frame(width: 60, alignment: .trailing)
            }

            HStack {
                Text(i18n.t(.settingsRmsLabel))
                Slider(value: $vm.silenceRmsThreshold, in: 0...0.01, step: 0.0001)
                Text(String(format: "%.4f", vm.silenceRmsThreshold))
                    .frame(width: 60, alignment: .trailing)
            }

            Toggle(i18n.t(.settingsDebugLabel), isOn: $vm.debugEnabled)
        }
    }
}

// MARK: - Window Controller

final class SettingsWindowController: NSWindowController {
    private let vm: SettingsViewModel

    init(settings: SettingsManager, i18n: I18n, onSave: @escaping () -> Void) {
        self.vm = SettingsViewModel(settings: settings)
        vm.load()

        let window = NSWindow(
            contentRect: .zero,
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: true
        )
        window.title = i18n.t(.settingsTitle)
        window.setContentSize(NSSize(width: 420, height: 350))
        window.center()
        window.isReleasedWhenClosed = false

        super.init(window: window)

        let view = SettingsView(vm: vm, i18n: i18n, onSave: {
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
