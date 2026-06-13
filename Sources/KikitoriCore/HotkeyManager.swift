import AppKit

/// Option キー監視。
public final class HotkeyManager: @unchecked Sendable {
    public var onKeyDown: (@Sendable () -> Void)?
    public var onKeyUp: (@Sendable () -> Void)?

    /// 現在ホットキーが押下中か（スレッドセーフ）
    public var isDown: Bool { lock.withLock { down } }

    private var global: Any?
    private var local: Any?
    private var down = false
    private let lock = NSLock()
    
    public init() {}
    
    public func start() {
        global = NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged) { [weak self] in
            self?.handle($0)
        }
        local = NSEvent.addLocalMonitorForEvents(matching: .flagsChanged) { [weak self] in
            self?.handle($0); return $0
        }
    }
    
    public func stop() {
        if let g = global { NSEvent.removeMonitor(g) }; global = nil
        if let l = local { NSEvent.removeMonitor(l) }; local = nil
    }
    
    private func handle(_ e: NSEvent) {
        guard e.type == .flagsChanged else { return }
        let opt = e.modifierFlags.intersection(.deviceIndependentFlagsMask).contains(.option)
        let (fireDown, fireUp): (Bool, Bool) = lock.withLock {
            if opt, !down { down = true; return (true, false) }
            if !opt, down { down = false; return (false, true) }
            return (false, false)
        }
        if fireDown { onKeyDown?() }
        if fireUp { onKeyUp?() }
    }
}
