import AppKit

/// 最前面アプリの PID を記憶・復元する。
public final class FrontmostAppTracker: @unchecked Sendable {
    private let lock = NSLock()
    private var capturedPID: pid_t?

    public init() {}

    /// 現在の最前面アプリの PID を記憶する。
    /// 録音開始時に呼ぶ。
    @discardableResult
    public func capture() -> pid_t? {
        let app = NSWorkspace.shared.frontmostApplication
        let pid = app?.processIdentifier
        lock.withLock { capturedPID = pid }
        return pid
    }

    /// 記憶した PID のアプリを再アクティブ化する。
    /// ペースト完了後にバックグラウンドスレッドで呼ぶ。
    public func restore() {
        let pid: pid_t? = lock.withLock { capturedPID }
        guard let pid else { return }

        guard let app = NSRunningApplication(processIdentifier: pid) else { return }
        app.activate(options: .activateAllWindows)
    }

    /// 現在記憶中の PID（テスト用）
    public var currentPID: pid_t? {
        lock.withLock { capturedPID }
    }
}
