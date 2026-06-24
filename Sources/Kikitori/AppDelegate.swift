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
        setupMainMenu()

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
        injector.onAccessibilityPermissionMissing = { [weak self] text in
            Task { @MainActor in
                guard let self else { return }
                AccessibilityDialogManager.shared.show(transcribedText: text, i18n: self.i18n)
            }
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

        Task { [weak self] in
            guard let self else { return }
            do {
                // 音声認識の準備が完了するまで待つ。これにより、
                // インジケーター表示前に認識エンジンが確実に音声を受け取れる状態になる。
                await r.start()

                // ホットキーが既に離されていれば（stop() が呼ばれていれば）
                // 録音を開始しない。オーバーレイも表示しない。
                guard self.recording else { return }

                // 無変換の生バッファを渡す。SpeechRecognizer 内の BufferConverter で
                // 認識エンジン向けフォーマットに変換する。ここで targetFormat を設定すると
                // Int16 バッファが渡され、無音判定 RMS 計算が float フォーマットを前提に
                // 動作しないため文字が認識されなくなる。
                c.targetFormat = nil
                c.onAudioBuffer = { r.addAudio($0) }
                self.overlay.show()
                try await c.start()
            } catch {
                self.recording = false
                self.overlay.hide()
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
        NSApp.activate(ignoringOtherApps: true)
        
        // もし起動時にスタートされていなければ（DEBUGなど）、ここでスタートさせる
        updater.startUpdater()
        
        updater.checkForUpdates(nil)
    }

    @objc func quit() {
        hotkey.stop()
        NSApp.terminate(nil)
    }

    // MARK: - Main Menu

    /// Set up NSApp.mainMenu with Edit menu so Cmd+C/V/X/A/Z shortcuts work
    /// in SwiftUI TextFields. Without a main menu, keyboard equivalents for
    /// standard editing commands are not routed to the first responder.
    private func setupMainMenu() {
        let mainMenu = NSMenu()

        // App submenu — required by convention even for accessory apps
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu()
        appMenuItem.submenu = appMenu
        appMenu.addItem(NSMenuItem(
            title: "Quit Kikitori",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        ))

        // Edit submenu — provides Copy, Paste, Cut, Undo, Redo, Select All
        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Edit")
        editMenuItem.submenu = editMenu

        editMenu.addItem(NSMenuItem(
            title: "Undo",
            action: Selector(("undo:")),
            keyEquivalent: "z"
        ))
        editMenu.addItem(NSMenuItem(
            title: "Redo",
            action: Selector(("redo:")),
            keyEquivalent: "Z"
        ))
        editMenu.addItem(.separator())
        editMenu.addItem(NSMenuItem(
            title: "Cut",
            action: #selector(NSText.cut(_:)),
            keyEquivalent: "x"
        ))
        editMenu.addItem(NSMenuItem(
            title: "Copy",
            action: #selector(NSText.copy(_:)),
            keyEquivalent: "c"
        ))
        editMenu.addItem(NSMenuItem(
            title: "Paste",
            action: #selector(NSText.paste(_:)),
            keyEquivalent: "v"
        ))
        editMenu.addItem(NSMenuItem(
            title: "Delete",
            action: #selector(NSText.delete(_:)),
            keyEquivalent: "\u{8}"
        ))
        editMenu.addItem(NSMenuItem(
            title: "Select All",
            action: #selector(NSText.selectAll(_:)),
            keyEquivalent: "a"
        ))

        NSApp.mainMenu = mainMenu
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
