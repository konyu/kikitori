import AppKit
import KikitoriCore

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var item: NSStatusItem!
    private let capture = AudioCapture()
    private let hotkey = HotkeyManager()
    private let injector = TextInjector()
    private let settings = SettingsManager()
    private let i18n = I18n()
    private let corrections = Corrections()
    private let tracker = FrontmostAppTracker()
    private var recognizer: SpeechRecognizer?
    private var recording = false
    private var autoStopTask: Task<Void, Never>?
    private var settingsWindow: SettingsWindowController?
    private var correctionsWindow: CorrectionsWindowController?
    private let overlay = OverlayController()

    func applicationDidFinishLaunching(_ n: Notification) {
        NSApp.setActivationPolicy(.accessory)
        settings.load()
        i18n.setLanguage(settings.uiLanguage)
        DebugLogger.enabled = settings.debug
        corrections.load()
        hotkey.config = HotkeyConfig.parse(from: settings.hotkey)
        capture.onAmplitude = { [weak self] amp in
            self?.overlay.updateAmplitude(amp)
        }

        item = NSStatusBar.system.statusItem(withLength: 24)
        if let btn = item.button {
            if let icon = IconLoader.loadIdleIcon() {
                icon.size = NSSize(width: 18, height: 18)
                btn.image = icon
            } else {
                btn.image = NSImage(systemSymbolName: "mic", accessibilityDescription: "Kikitori")
            }
        }
        let m = NSMenu()
        let settingsItem = NSMenuItem(title: i18n.t(.menuSettings), action: #selector(showSettings), keyEquivalent: ",")
        settingsItem.target = self
        m.addItem(settingsItem)
        
        let correctionsItem = NSMenuItem(title: i18n.t(.menuCorrections), action: #selector(showCorrections), keyEquivalent: "e")
        correctionsItem.target = self
        m.addItem(correctionsItem)
        
        m.addItem(.separator())
        let quitItem = NSMenuItem(title: i18n.t(.menuQuit), action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        m.addItem(quitItem)
        item.menu = m

        hotkey.onKeyDown = { [weak self] in
            Task { @MainActor in
                self?.tracker.capture()
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

        // 録音開始時に常に最新のファイル内容を読み込む
        settings.load()
        corrections.load()

        let r = SpeechRecognizer()
        r.language = settings.language
        r.minDurationMs = settings.minDurationMs
        r.silenceRmsThreshold = settings.silenceRmsThreshold
        recognizer = r
        let c = capture

        // 自動停止タイマー
        scheduleAutoStop()

        Task {
            do {
                r.start()
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
            DebugLogger.log("stop() ignored: not recording")
            return
        }
        recording = false
        DebugLogger.log("stop() - cancelling autoStop, stopping capture")
        cancelAutoStop()
        capture.stop()
        overlay.hide()

        let r = recognizer; recognizer = nil
        guard let r else {
            DebugLogger.log("stop() - no recognizer")
            return
        }
        Task {
            let text = await r.stop()
            DebugLogger.log("stop() - recognizer returned: '\(text)'")
            var final = text
            if !final.isEmpty {
                final = corrections.apply(to: final)
                DebugLogger.log("stop() - after corrections: '\(final)'")
            }
            if !final.isEmpty {
                DebugLogger.log("stop() - injecting: '\(final)'")
                injector.inject(final)
            } else {
                DebugLogger.log("stop() - empty text, skipping inject")
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
            settingsWindow = SettingsWindowController(settings: settings, i18n: i18n, onSave: { [weak self] in
                self?.reloadSettings()
            })
        }
        settingsWindow?.show()
    }

    @objc func showCorrections() {
        if correctionsWindow == nil {
            correctionsWindow = CorrectionsWindowController(corrections: corrections, i18n: i18n)
        }
        correctionsWindow?.show()
    }

    private func reloadSettings() {
        settings.load()
        i18n.setLanguage(settings.uiLanguage)
        DebugLogger.enabled = settings.debug
        hotkey.config = HotkeyConfig.parse(from: settings.hotkey)
        
        if let m = item.menu {
            m.items[0].title = i18n.t(.menuSettings)
            m.items[1].title = i18n.t(.menuCorrections)
            m.items[3].title = i18n.t(.menuQuit)
        }
        
        settingsWindow?.window?.title = i18n.t(.settingsTitle)
        correctionsWindow?.window?.title = i18n.t(.correctionsTitle)
    }

    @objc func quit() {
        hotkey.stop()
        NSApp.terminate(nil)
    }
}
