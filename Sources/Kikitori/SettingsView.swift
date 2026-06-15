import SwiftUI
import KikitoriCore
import ServiceManagement

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
    @Published var launchAtLogin: Bool = false

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
        launchAtLogin = SMAppService.mainApp.status == .enabled
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
        
        do {
            if launchAtLogin {
                if SMAppService.mainApp.status != .enabled {
                    try SMAppService.mainApp.register()
                }
            } else {
                if SMAppService.mainApp.status == .enabled {
                    try SMAppService.mainApp.unregister()
                }
            }
        } catch {
            print("Failed to toggle launch at login: \(error)")
        }
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
    static let languageOptions: [(String, String)] = [
        ("ja", "日本語"),
        ("en", "English"),
        ("zh", "中文"),
        ("ko", "한국어"),
        ("fr", "Français"),
        ("de", "Deutsch"),
    ]
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
                filtersTab
                    .tabItem { Label(i18n.t(.tabFilters), systemImage: "waveform") }
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
        .frame(width: 440, height: 400)
    }

    private var generalTab: some View {
        ScrollView {
            VStack(spacing: 0) {
                // ---- 言語設定 ----
                GroupBox {
                    VStack(spacing: 12) {
                        settingsRow {
                            Picker(i18n.t(.settingsLanguageLabel), selection: $vm.language) {
                                ForEach(SettingsViewModel.languageOptions, id: \.0) { code, label in
                                    Text(label).tag(code)
                                }
                            }
                            .frame(width: 160)
                        }
                        settingsRow {
                            Picker(i18n.t(.settingsUILanguageLabel), selection: $vm.uiLanguage) {
                                Text("日本語").tag("ja")
                                Text("English").tag("en")
                            }
                            .frame(width: 160)
                        }
                    }
                    .padding(.vertical, 8)
                } label: {
                    Text(i18n.t(.settingsLanguageLabel)).font(.headline)
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)

                // ---- 起動 ----
                Toggle(isOn: $vm.launchAtLogin) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(i18n.t(.settingsLaunchAtLogin))
                            .font(.body)
                        Text("macOSの「ログイン項目と機能拡張」に追加されます")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .toggleStyle(.switch)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)

                Divider()
                    .padding(.vertical, 8)

                // ---- ホットキー ----
                GroupBox {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(i18n.t(.settingsHotkeyLabel))
                            .font(.headline)
                        
                        Divider()
                        
                        Toggle("Fn     🌐", isOn: $vm.hotkeyFn)
                        Toggle("Control ⌃", isOn: $vm.hotkeyCtrl)
                        Toggle("Option ⌥", isOn: $vm.hotkeyAlt)
                        Toggle("Command ⌘", isOn: $vm.hotkeyCmd)
                        Toggle("Shift   ⇧", isOn: $vm.hotkeyShift)
                    }
                    .padding(.vertical, 8)
                }
                .padding(.horizontal, 16)

                // ---- リセット ----
                HStack {
                    Spacer()
                    Button(i18n.t(.settingsResetBtn)) { vm.reset() }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
        }
    }

    private func settingsRow<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        HStack {
            content()
            Spacer()
        }
    }

    private var filtersTab: some View {
        ScrollView {
            VStack(spacing: 0) {
                // ---- 録音時間 ----
                GroupBox {
                    VStack(spacing: 14) {
                        sliderRow(
                            label: i18n.t(.settingsMinDurLabel),
                            hint: i18n.t(.settingsMinDurHint),
                            value: $vm.minDurationMs,
                            range: 100...5000,
                            step: 100,
                            format: { "\(Int($0))\(i18n.t(.msUnit))" }
                        )
                        sliderRow(
                            label: i18n.t(.settingsMaxDurLabel),
                            value: $vm.maxDurationSec,
                            range: 10...300,
                            step: 10,
                            format: { "\(Int($0))\(i18n.t(.secUnit))" }
                        )
                    }
                    .padding(.vertical, 8)
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)

                // ---- 無音判定 ----
                GroupBox {
                    VStack(spacing: 10) {
                        sliderRow(
                            label: i18n.t(.settingsRmsLabel),
                            value: $vm.silenceRmsThreshold,
                            range: 0...0.01,
                            step: 0.0001,
                            format: { String(format: "%.4f", $0) }
                        )
                    }
                    .padding(.vertical, 8)
                }
                .padding(.horizontal, 16)
                .padding(.top, 12)

                // ---- デバッグ ----
                Toggle(isOn: $vm.debugEnabled) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(i18n.t(.settingsDebugLabel))
                            .font(.body)
                        Text("ログを ~/Library/Logs/Kikitori/ に出力します")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .toggleStyle(.switch)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
        }
    }

    private func sliderRow(
        label: String,
        hint: String? = nil,
        value: Binding<Double>,
        range: ClosedRange<Double>,
        step: Double,
        format: @escaping (Double) -> String
    ) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(label)
                    .frame(width: 120, alignment: .leading)
                Slider(value: value, in: range, step: step)
                Text(format(value.wrappedValue))
                    .frame(width: 60, alignment: .trailing)
                    .monospacedDigit()
            }
            if let hint = hint {
                Text(hint)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.leading, 120)
            }
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
        window.setContentSize(NSSize(width: 440, height: 460))
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
