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

    func applicationDidFinishLaunching(_ n: Notification) {
        settings.load()
        corrections.load()
        hotkey.config = HotkeyConfig.parse(from: settings.hotkey)

        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = item.button {
            btn.image = NSImage(systemSymbolName: "mic", accessibilityDescription: "Kikitori")
        }
        let m = NSMenu()
        m.addItem(NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q"))
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

        let r = SpeechRecognizer()
        r.minDurationMs = settings.minDurationMs
        r.silenceRmsThreshold = settings.silenceRmsThreshold
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
            NSLog("[Kikitori] stop() ignored: not recording")
            return
        }
        recording = false
        NSLog("[Kikitori] stop() - cancelling autoStop, stopping capture")
        cancelAutoStop()
        capture.stop()

        let r = recognizer; recognizer = nil
        guard let r else {
            NSLog("[Kikitori] stop() - no recognizer")
            return
        }
        Task {
            let text = await r.stop()
            NSLog("[Kikitori] stop() - recognizer returned: '\(text)'")
            var final = text
            if !final.isEmpty {
                final = corrections.apply(to: final)
                NSLog("[Kikitori] stop() - after corrections: '\(final)'")
            }
            if !final.isEmpty {
                NSLog("[Kikitori] stop() - injecting: '\(final)'")
                injector.inject(final)
            } else {
                NSLog("[Kikitori] stop() - empty text, skipping inject")
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

    @objc private func quit() {
        hotkey.stop()
        NSApp.terminate(nil)
    }
}
