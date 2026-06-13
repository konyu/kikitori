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

    /// 修飾キーベースのホットキーで、現在の修飾キーが必要条件を満たしているか
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

    private func handleFlagsChanged(_ e: NSEvent) {
        guard e.type == .flagsChanged else { return }
        let flags = e.modifierFlags.intersection(.deviceIndependentFlagsMask)

        switch config {
        case .option, .modifiers:
            let target = config.modifierFlags
            let satisfied = flags.contains(target)
            let (fireDown, fireUp): (Bool, Bool) = lock.withLock {
                modifiersSatisfied = satisfied
                if satisfied, !_down { _down = true; return (true, false) }
                if !satisfied, _down { _down = false; return (false, true) }
                return (false, false)
            }
            if fireDown { onKeyDown?() }
            if fireUp { onKeyUp?() }

        case .key(let mods, let keyCode):
            // 修飾キー状態だけ更新。キー押下は handleKeyEvent で処理。
            let targetMods: NSEvent.ModifierFlags = mods.reduce(into: []) { $0.formUnion($1.flag) }
            let satisfied = flags.contains(targetMods)
            lock.withLock { modifiersSatisfied = satisfied }

            // 修飾キーが不足したら即アップ
            if !satisfied {
                let wasDown: Bool = lock.withLock {
                    if _down { _down = false; return true }
                    return false
                }
                if wasDown { onKeyUp?() }
            }
        }
    }

    private func handleKeyEvent(_ e: NSEvent, down: Bool) {
        guard case .key(let mods, let targetKeyCode) = config else { return }

        let satisfied: Bool = lock.withLock { modifiersSatisfied }
        guard satisfied else {
            // 修飾キー不足時はキー解放チェック
            if !down, e.keyCode == targetKeyCode {
                let wasDown: Bool = lock.withLock {
                    if _down { _down = false; return true }
                    return false
                }
                if wasDown { onKeyUp?() }
            }
            return
        }

        if down, e.keyCode == targetKeyCode {
            let shouldFire: Bool = lock.withLock {
                if !_down { _down = true; return true }
                return false
            }
            if shouldFire { onKeyDown?() }
        }

        if !down, e.keyCode == targetKeyCode {
            let wasDown: Bool = lock.withLock {
                if _down { _down = false; return true }
                return false
            }
            if wasDown { onKeyUp?() }
        }
    }
}
