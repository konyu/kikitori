import AppKit
import KikitoriCore

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var item: NSStatusItem!
    private let capture = AudioCapture()
    private let hotkey = HotkeyManager()
    private let injector = TextInjector()
    private var recognizer: SpeechRecognizer?
    private var recording = false
    
    func applicationDidFinishLaunching(_ n: Notification) {
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = item.button {
            btn.image = NSImage(systemSymbolName: "mic", accessibilityDescription: "Kikitori")
        }
        let m = NSMenu()
        m.addItem(NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q"))
        item.menu = m
        
        hotkey.onKeyDown = { [weak self] in Task { @MainActor in self?.start() } }
        hotkey.onKeyUp   = { [weak self] in Task { @MainActor in self?.stop() } }
        hotkey.start()
    }
    
    private func start() {
        guard !recording else { return }
        recording = true
        let r = SpeechRecognizer()
        recognizer = r
        let c = capture
        
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
        guard recording else { return }
        recording = false
        capture.stop()
        let r = recognizer; recognizer = nil
        guard let r else { return }
        Task {
            let text = await r.stop()
            if !text.isEmpty { injector.inject(text) }
        }
    }
    
    @objc private func quit() {
        hotkey.stop()
        NSApp.terminate(nil)
    }
}
