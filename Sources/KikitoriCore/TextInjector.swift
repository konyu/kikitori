import AppKit

// MARK: - Frontmost App Tracker

/// 最前面アプリの PID を記憶・復元する。
public final class FrontmostAppTracker: @unchecked Sendable {
    private let lock = NSLock()
    private var capturedPID: pid_t?

    public init() {}

    @discardableResult
    public func capture() -> pid_t? {
        let app = NSWorkspace.shared.frontmostApplication
        let pid = app?.processIdentifier
        lock.withLock { capturedPID = pid }
        return pid
    }

    public func restore() {
        let pid: pid_t? = lock.withLock { capturedPID }
        guard let pid else { return }
        guard let app = NSRunningApplication(processIdentifier: pid) else { return }
        app.activate(options: .activateAllWindows)
    }
}

// MARK: - Text Injector

/// テキスト注入。クリップボード経由 Cmd+V でテキストを貼り付ける。
/// 注入前に元のクリップボードを保存し、注入後に復元する。
public final class TextInjector: @unchecked Sendable {
    private let lock = NSLock()
    private var pendingOriginal: String?
    private var restoreGeneration: Int = 0

    public init() {}

    public func inject(_ text: String) {
        guard !text.isEmpty else { return }

        // 元のクリップボードを保存（初回注入時のみ）
        var original: String?
        var gen: Int = 0
        lock.withLock {
            if restoreGeneration == 0 {
                pendingOriginal = NSPasteboard.general.string(forType: .string)
            }
            restoreGeneration += 1
            gen = restoreGeneration
            original = pendingOriginal
        }

        // テキストをクリップボードにコピー
        let pb = NSPasteboard.general
        pb.clearContents()
        pb.setString(text, forType: .string)

        // Cmd+V
        let src = CGEventSource(stateID: .combinedSessionState)
        let d = CGEvent(keyboardEventSource: src, virtualKey: 0x09, keyDown: true)
        let u = CGEvent(keyboardEventSource: src, virtualKey: 0x09, keyDown: false)
        d?.flags = .maskCommand; u?.flags = .maskCommand
        d?.post(tap: .cghidEventTap); u?.post(tap: .cghidEventTap)

        // 元のクリップボードを非同期で復元
        if let original, !original.isEmpty {
            Task.detached { [weak self] in
                // Cmd+V が処理されるのを待つ
                try? await Task.sleep(nanoseconds: 50_000_000)
                guard let self else { return }
                let shouldRestore: Bool = self.lock.withLock {
                    if gen != self.restoreGeneration { return false }  // 新しい注入あり
                    self.restoreGeneration = 0
                    self.pendingOriginal = nil
                    return true
                }
                if shouldRestore {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(original, forType: .string)
                }
            }
        }
    }
}
