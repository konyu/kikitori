import Foundation

/// デバッグログ出力。`SettingsManager.debug` が `true` の時のみ NSLog 出力。
public final class DebugLogger: @unchecked Sendable {
    public static let shared = DebugLogger()

    public var enabled: Bool = false

    public init() {}

    public func log(_ message: @autoclosure () -> String) {
        guard enabled else { return }
        NSLog("[Kikitori] %@", message())
    }
}
