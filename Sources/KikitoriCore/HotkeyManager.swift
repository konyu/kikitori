import AppKit

/// グローバルホットキー監視。
/// Option 単体の他、修飾キー組み合わせや修飾+文字キーに対応。
public final class HotkeyManager: @unchecked Sendable {
    public var onKeyDown: (@Sendable () -> Void)?
    public var onKeyUp: (@Sendable () -> Void)?

    /// 現在ホットキーが押下中か（スレッドセーフ）
    public var isDown: Bool { lock.withLock { _down } }

    /// ホットキー設定（デフォルト: Option）
    public var config: HotkeyConfig = .option {
        didSet { updateMonitoring() }
    }

    private var globalFlags: Any?
    private var globalKeyDown: Any?
    private var globalKeyUp: Any?
    private var localFlags: Any?
    private var localKeyDown: Any?
    private var localKeyUp: Any?

    private var _down = false
    private let lock = NSLock()
    private var modifiersSatisfied = false

    public init() {}

    // MARK: - Start / Stop

    public func start() {
        stop()
        updateMonitoring()
    }

    public func stop() {
        removeAllMonitors()
    }

    private func updateMonitoring() {
        removeAllMonitors()
        let fmask: NSEvent.EventTypeMask = .flagsChanged
        globalFlags = NSEvent.addGlobalMonitorForEvents(matching: fmask) { [weak self] in
            self?.handleFlagsChanged($0)
        }
        localFlags = NSEvent.addLocalMonitorForEvents(matching: fmask) { [weak self] e in
            self?.handleFlagsChanged(e); return e
        }

        if config.needsKeyMonitoring {
            globalKeyDown = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] in
                self?.handleKeyEvent($0, down: true)
            }
            globalKeyUp = NSEvent.addGlobalMonitorForEvents(matching: .keyUp) { [weak self] in
                self?.handleKeyEvent($0, down: false)
            }
            localKeyDown = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] e in
                self?.handleKeyEvent(e, down: true); return e
            }
            localKeyUp = NSEvent.addLocalMonitorForEvents(matching: .keyUp) { [weak self] e in
                self?.handleKeyEvent(e, down: false); return e
            }
        }
    }

    private func removeAllMonitors() {
        if let m = globalFlags { NSEvent.removeMonitor(m) }; globalFlags = nil
        if let m = globalKeyDown { NSEvent.removeMonitor(m) }; globalKeyDown = nil
        if let m = globalKeyUp { NSEvent.removeMonitor(m) }; globalKeyUp = nil
        if let m = localFlags { NSEvent.removeMonitor(m) }; localFlags = nil
        if let m = localKeyDown { NSEvent.removeMonitor(m) }; localKeyDown = nil
        if let m = localKeyUp { NSEvent.removeMonitor(m) }; localKeyUp = nil
    }

    // MARK: - Event Handling

    /// _down のアトミックな状態遷移。true → fire down, false → fire up
    private func _transition(wantDown: Bool) -> (fireDown: Bool, fireUp: Bool) {
        lock.withLock {
            modifiersSatisfied = wantDown
            if wantDown, !_down { _down = true; return (true, false) }
            if !wantDown, _down { _down = false; return (false, true) }
            return (false, false)
        }
    }

    private func handleFlagsChanged(_ e: NSEvent) {
        let flags = e.modifierFlags.intersection(.deviceIndependentFlagsMask)
        let satisfied = flags.contains(config.modifierFlags)

        switch config {
        case .option, .modifiers:
            let (fireDown, fireUp) = _transition(wantDown: satisfied)
            if fireDown { onKeyDown?() }
            if fireUp { onKeyUp?() }

        case .key:
            lock.withLock { modifiersSatisfied = satisfied }
            if !satisfied {
                let (_, fireUp) = _transition(wantDown: false)
                if fireUp { onKeyUp?() }
            }
        }
    }

    private func handleKeyEvent(_ e: NSEvent, down: Bool) {
        guard case .key(_, let targetKeyCode) = config else { return }
        guard e.keyCode == targetKeyCode else { return }

        let s: Bool = lock.withLock { modifiersSatisfied }
        guard s else {
            if !down {
                let (_, fireUp) = _transition(wantDown: false)
                if fireUp { onKeyUp?() }
            }
            return
        }

        if down {
            let (fireDown, _) = _transition(wantDown: true)
            if fireDown { onKeyDown?() }
        } else {
            let (_, fireUp) = _transition(wantDown: false)
            if fireUp { onKeyUp?() }
        }
    }
}
