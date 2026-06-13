import SwiftUI
import KikitoriCore

// MARK: - ViewModel

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var language: String = "ja"
    @Published var uiLanguage: String = "ja"
    @Published var hotkeyText: String = "option"
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
        hotkeyText = settings.hotkey.joined(separator: ", ")
        minDurationMs = Double(settings.minDurationMs)
        maxDurationSec = Double(settings.maxDurationSec)
        silenceRmsThreshold = settings.silenceRmsThreshold
        debugEnabled = settings.debug
    }

    func save() {
        settings.language = language
        settings.uiLanguage = uiLanguage
        settings.hotkey = hotkeyText.split(separator: ",").map {
            $0.trimmingCharacters(in: .whitespaces)
        }
        settings.minDurationMs = Int(minDurationMs)
        settings.maxDurationSec = Int(maxDurationSec)
        settings.silenceRmsThreshold = silenceRmsThreshold
        settings.debug = debugEnabled
        settings.save()
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
    let onDismiss: () -> Void

    var body: some View {
        TabView {
            generalTab
                .tabItem { Label("一般", systemImage: "gearshape") }
            filtersTab
                .tabItem { Label("フィルタ", systemImage: "waveform") }
        }
        .padding()
        .frame(width: 420, height: 320)
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

            HStack {
                Text("ホットキー:")
                TextField("option", text: $vm.hotkeyText)
                    .frame(width: 200)
                Text("(例: ctrl, shift  /  cmd, space  /  f13)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            HStack {
                Spacer()
                Button("デフォルトに戻す") { vm.reset() }
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

            HStack {
                Spacer()
                Button("キャンセル") { onDismiss() }
                Button("保存して適用") {
                    vm.save()
                    onDismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
            .padding(.top)
        }
    }
}

// MARK: - Window Controller

final class SettingsWindowController: NSWindowController {
    private let vm: SettingsViewModel

    init(settings: SettingsManager, onDismiss: @escaping () -> Void) {
        self.vm = SettingsViewModel(settings: settings)
        vm.load()

        let view = SettingsView(vm: vm, onDismiss: onDismiss)
        let hosting = NSHostingController(rootView: view)

        let window = NSWindow(contentViewController: hosting)
        window.title = "Kikitori 設定"
        window.styleMask = [.titled, .closable, .miniaturizable]
        window.setContentSize(NSSize(width: 420, height: 320))
        window.center()
        window.isReleasedWhenClosed = false

        super.init(window: window)
    }

    required init?(coder: NSCoder) { fatalError() }

    func show() {
        vm.load()
        window?.center()
        showWindow(nil)
    }
}
