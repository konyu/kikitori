import AppKit
import KikitoriCore

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var item: NSStatusItem!
    private let capture = AudioCapture()
    private let hotkey = HotkeyManager()
    private let injector = TextInjector()
    private let settings = SettingsManager()
    private let corrections = Corrections()
    private let tracker = FrontmostAppTracker()
    private var recognizer: SpeechRecognizer?
    private var recording = false
    private var autoStopTask: Task<Void, Never>?
    private var settingsWindow: SettingsWindowController?
    private let overlay = OverlayController()

    func applicationDidFinishLaunching(_ n: Notification) {
        settings.load()
        DebugLogger.shared.enabled = settings.debug
        corrections.load()
        hotkey.config = HotkeyConfig.parse(from: settings.hotkey)
        capture.onAmplitude = { [weak self] amp in
            self?.overlay.updateAmplitude(amp)
        }

        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = item.button {
            if let icon = IconLoader.loadIdleIcon() {
                // メニューバーアイコンがシステム再描画時に消えるバグを防ぐため、
                // 正しく新しい NSImage コンテキストに描画（リサイズ）する
                let ratio = icon.size.width / icon.size.height
                let newSize = NSSize(width: 18 * ratio, height: 18)
                let resized = NSImage(size: newSize)
                resized.lockFocus()
                icon.draw(in: NSRect(origin: .zero, size: newSize),
                          from: NSRect(origin: .zero, size: icon.size),
                          operation: .sourceOver,
                          fraction: 1.0)
                resized.unlockFocus()
                resized.isTemplate = true
                btn.image = resized
            } else {
                btn.image = NSImage(systemSymbolName: "mic", accessibilityDescription: "Kikitori")
            }
        }
        let m = NSMenu()
        let settingsItem = NSMenuItem(title: "Settings", action: #selector(showSettings), keyEquivalent: ",")
        settingsItem.target = self
        m.addItem(settingsItem)
        m.addItem(.separator())
        let quitItem = NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        m.addItem(quitItem)
        item.menu = m

        hotkey.onKeyDown = { [weak self] in
            Task { @MainActor in
                self?.tracker.capture()  // 初回押下時のみ PID 記憶
                self?.start()
            }
        }
        hotkey.onKeyUp   = { [weak self] in Task { @MainActor in self?.stop() } }
        hotkey.start()
    }

    private func start() {
        guard !recording else { return }
        recording = true

        overlay.show()

        let r = SpeechRecognizer()
        r.language = settings.language
        r.minDurationMs = settings.minDurationMs
        r.silenceRmsThreshold = settings.silenceRmsThreshold
        r.contextualStrings = settings.glossary
        recognizer = r
        let c = capture

        // 自動停止タイマー
        scheduleAutoStop()

        Task {
            do {
                try await r.start()
                if let f = r.compatibleAudioFormat { c.targetFormat = f }
                c.onAudioBuffer = { r.addAudio($0) }
                try await c.start()
            } catch {
                await MainActor.run { [weak self] in self?.recording = false }
            }
        }
    }

    private func stop() {
        guard recording else {
            DebugLogger.shared.log("stop() ignored: not recording")
            return
        }
        recording = false
        DebugLogger.shared.log("stop() - cancelling autoStop, stopping capture")
        cancelAutoStop()
        capture.stop()
        overlay.hide()

        let r = recognizer; recognizer = nil
        guard let r else {
            DebugLogger.shared.log("stop() - no recognizer")
            return
        }
        Task {
            let text = await r.stop()
            DebugLogger.shared.log("stop() - recognizer returned: '\(text)'")
            var final = text
            if !final.isEmpty {
                final = corrections.apply(to: final)
                DebugLogger.shared.log("stop() - after corrections: '\(final)'")
            }
            if !final.isEmpty {
                DebugLogger.shared.log("stop() - injecting: '\(final)'")
                injector.inject(final)
            } else {
                DebugLogger.shared.log("stop() - empty text, skipping inject")
            }
            Task.detached { [weak self] in self?.tracker.restore() }
        }
    }

    // MARK: - Auto-Stop

    private func scheduleAutoStop() {
        cancelAutoStop()
        let dur = settings.maxDurationSec
        autoStopTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(dur) * 1_000_000_000)
            guard !Task.isCancelled else { return }
            await MainActor.run { [weak self] in self?.handleAutoStop() }
        }
    }

    private func cancelAutoStop() {
        autoStopTask?.cancel()
        autoStopTask = nil
    }

    private func handleAutoStop() {
        guard recording else { return }
        // 現在の録音を停止・処理
        stop()

        // キーがまだ押されていれば再録音開始
        if hotkey.isDown {
            start()
        }
    }

    @objc func showSettings() {
        if settingsWindow == nil {
            settingsWindow = SettingsWindowController(settings: settings, onSave: { [weak self] in
                self?.reloadSettings()
            })
        }
        settingsWindow?.show()
    }

    private func reloadSettings() {
        settings.load()
        DebugLogger.shared.enabled = settings.debug
        hotkey.config = HotkeyConfig.parse(from: settings.hotkey)
    }

    @objc func quit() {
        hotkey.stop()
        NSApp.terminate(nil)
    }
}
