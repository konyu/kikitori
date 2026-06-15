import Foundation

// MARK: - Debug Logger

/// デバッグログ出力。`SettingsManager.debug` が `true` の時のみ NSLog 出力。
public enum DebugLogger {
    nonisolated(unsafe) public static var enabled: Bool = false

    public static func log(_ message: @autoclosure () -> String) {
        guard enabled else { return }
        NSLog("[Kikitori] %@", message())
    }
}

// MARK: - Simple YAML

/// シンプルな YAML パーサー。Kikitori 設定ファイル専用（ネスト浅いキー・値のみ対応）。
enum SimpleYAML {
    /// 文字列をパースして [String: String] 辞書を返す。
    /// - `#` で始まる行はコメント
    /// - `key: value` 形式のみ対応（値は文字列として扱う）
    /// - インデントのある階層は未対応
    static func parse(_ text: String) -> [String: String] {
        var result: [String: String] = [:]
        result.reserveCapacity(16)
        var buffer = ""
        for char in text {
            if char == "\n" {
                _parseLine(buffer, into: &result)
                buffer = ""
            } else {
                buffer.append(char)
            }
        }
        _parseLine(buffer, into: &result)
        return result
    }

    private static func _parseLine(_ raw: String, into result: inout [String: String]) {
        // コメント・空行・リスト行スキップ
        let trimmed = _trimLeft(raw)
        guard !trimmed.isEmpty, trimmed.first != "#", !trimmed.hasPrefix("- ") else { return }
        guard let colon = trimmed.firstIndex(of: ":") else { return }
        let key = _stripQuotes(_trimRight(String(trimmed[..<colon])))
        guard !key.isEmpty else { return }
        var value = _trimLeft(_trimRight(String(trimmed[trimmed.index(after: colon)...])))
        // クォート除去
        value = _stripQuotes(value)
        result[key] = value
    }

    /// 左空白除去（インプレース判定）
    private static func _trimLeft(_ s: String) -> String {
        var i = s.startIndex
        while i < s.endIndex, s[i].isWhitespace { i = s.index(after: i) }
        if i == s.startIndex { return s }
        return String(s[i...])
    }

    /// 右空白除去
    private static func _trimRight(_ s: String) -> String {
        var i = s.endIndex
        while i > s.startIndex {
            let prev = s.index(before: i)
            if !s[prev].isWhitespace { break }
            i = prev
        }
        if i == s.endIndex { return s }
        return String(s[..<i])
    }

    /// クォート除去（"..." または '...'）
    private static func _stripQuotes(_ s: String) -> String {
        guard s.count >= 2 else { return s }
        let first = s.first!, last = s.last!
        if (first == "\"" && last == "\"") || (first == "'" && last == "'") {
            return String(s.dropFirst().dropLast())
        }
        return s
    }

    /// 辞書を YAML 文字列に変換。
    static func serialize(_ dict: [String: String]) -> String {
        let sorted = dict.sorted { $0.key < $1.key }
        var result = ""
        result.reserveCapacity(sorted.count * 32)
        for (key, value) in sorted {
            let escaped = value.contains(" ") ? "\"\(value)\"" : value
            result += "\(key): \(escaped)\n"
        }
        return result
    }
}
