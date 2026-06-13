import AppKit

public struct TextInjector: Sendable {
    public init() {}
    public func inject(_ text: String) {
        guard !text.isEmpty else { return }
        let pb = NSPasteboard.general
        pb.clearContents()
        pb.setString(text, forType: .string)
        let src = CGEventSource(stateID: .combinedSessionState)
        let d = CGEvent(keyboardEventSource: src, virtualKey: 0x09, keyDown: true)
        let u = CGEvent(keyboardEventSource: src, virtualKey: 0x09, keyDown: false)
        d?.flags = .maskCommand; u?.flags = .maskCommand
        d?.post(tap: .cghidEventTap); u?.post(tap: .cghidEventTap)
    }
}
