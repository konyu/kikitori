import AppKit
import KikitoriCore
import Sparkle

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
    private let updater = SPUStandardUpdaterController(
        startingUpdater: false,
        updaterDelegate: nil,
        userDriverDelegate: nil
    )
    private var menuSettingsItem: NSMenuItem?
    private var menuCorrectionsItem: NSMenuItem?
    private var menuCheckUpdatesItem: NSMenuItem?
    private var menuQuitItem: NSMenuItem?

    func applicationDidFinishLaunching(_ n: Notification) {
        NSApp.setActivationPolicy(.accessory)

        // 起動時にマイク・音声認識権限をチェックし、未許可なら許可を求める。
        // 権限ダイアログは非同期で表示され、以降のセットアップをブロックしない。
        Task { @MainActor in
            await requestPermissionsIfNeeded()
        }

        // 開発中など appcast.xml がない環境で起動時にエラーダイアログが出るのを防ぐため、
        // 最初の起動時（かつまだチェックしたことがない場合のみ）バックグラウンドチェックを遅延させるか、
        // 単純に startingUpdater: false にして手動でスタートさせます。
        #if !DEBUG
        updater.startUpdater()
        #endif
        settings.load()
        i18n.setLanguage(settings.uiLanguage)
        DebugLogger.enabled = settings.debug
        corrections.load()
        hotkey.config = HotkeyConfig.parse(from: settings.hotkey)
        capture.onAmplitude = { [weak self] amp in
            self?.overlay.updateAmplitude(amp)
        }

        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = item.button {
            if let icon = IconLoader.loadIdleIcon() {
                let ratio = icon.size.height > 0 ? icon.size.width / icon.size.height : 1.0
                icon.size = NSSize(width: 18 * ratio, height: 18)
                btn.image = icon
            } else {
                btn.image = NSImage(systemSymbolName: "mic", accessibilityDescription: "Kikitori")
            }
        }
        let m = NSMenu()
        let settingsItem = NSMenuItem(title: i18n.t(.menuSettings), action: #selector(showSettings), keyEquivalent: ",")
        settingsItem.target = self
        menuSettingsItem = settingsItem
        m.addItem(settingsItem)

        let correctionsItem = NSMenuItem(title: i18n.t(.menuCorrections), action: #selector(showCorrections), keyEquivalent: "e")
        correctionsItem.target = self
        menuCorrectionsItem = correctionsItem
        m.addItem(correctionsItem)

        m.addItem(.separator())
        let updateItem = NSMenuItem(title: i18n.t(.menuCheckUpdates), action: #selector(checkForUpdates), keyEquivalent: "")
        updateItem.target = self
        menuCheckUpdatesItem = updateItem
        m.addItem(updateItem)

        m.addItem(.separator())
        let quitItem = NSMenuItem(title: i18n.t(.menuQuit), action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menuQuitItem = quitItem
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
        
        menuSettingsItem?.title = i18n.t(.menuSettings)
        menuCorrectionsItem?.title = i18n.t(.menuCorrections)
        menuCheckUpdatesItem?.title = i18n.t(.menuCheckUpdates)
        menuQuitItem?.title = i18n.t(.menuQuit)
        
        settingsWindow?.window?.title = i18n.t(.settingsTitle)
        correctionsWindow?.window?.title = i18n.t(.correctionsTitle)
    }

    @objc func checkForUpdates() {
        updater.checkForUpdates(nil)
    }

    @objc func quit() {
        hotkey.stop()
        NSApp.terminate(nil)
    }

    // MARK: - Permissions

    /// 起動時にマイクと音声認識の権限をチェック・要求する。
    /// ユーザーがこの起動で初めて拒否した場合のみ説明アラートを表示する。
    private func requestPermissionsIfNeeded() async {
        let micBefore = PermissionManager.shared.microphoneStatus
        let micDenied = micBefore.needsRequest
            ? await PermissionManager.shared.requestMicrophonePermission() == .denied
            : false

        let speechBefore = PermissionManager.shared.speechRecognitionStatus
        let speechDenied = speechBefore.needsRequest
            ? await PermissionManager.shared.requestSpeechRecognitionPermission() == .denied
            : false

        guard micDenied || speechDenied else { return }

        DebugLogger.log("Permission denied by user: mic=\(micDenied), speech=\(speechDenied)")
        showPermissionDeniedAlert()
    }

    private func showPermissionDeniedAlert() {
        let alert = NSAlert()
        alert.messageText = i18n.t(.permissionDeniedTitle)
        alert.informativeText = i18n.t(.permissionDeniedMessage)
        alert.alertStyle = .warning
        alert.addButton(withTitle: i18n.t(.permissionOpenSettings))
        alert.addButton(withTitle: i18n.t(.permissionOK))

        let result = alert.runModal()
        if result == .alertFirstButtonReturn {
            // プライバシー設定のマイク欄を開く
            if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone") {
                NSWorkspace.shared.open(url)
            }
        }
    }
}
