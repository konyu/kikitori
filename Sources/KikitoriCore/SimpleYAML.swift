import Foundation

/// シンプルな YAML パーサー。Kikitori 設定ファイル専用（ネスト浅いキー・値のみ対応）。
enum SimpleYAML {
    /// 文字列をパースして [String: String] 辞書を返す。
    /// - `#` で始まる行はコメント
    /// - `key: value` 形式のみ対応（値は文字列として扱う）
    /// - インデントのある階層は未対応
    static func parse(_ text: String) -> [String: String] {
        var result: [String: String] = [:]
        for line in text.split(separator: "\n", omittingEmptySubsequences: false) {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard !trimmed.isEmpty, !trimmed.hasPrefix("#") else { continue }
            guard !trimmed.hasPrefix("- ") else { continue }  // リスト行はスキップ
            guard let colon = trimmed.firstIndex(of: ":") else { continue }
            let key = String(trimmed[..<colon]).trimmingCharacters(in: .whitespaces)
            var value = String(trimmed[trimmed.index(after: colon)...]).trimmingCharacters(in: .whitespaces)
            // クォート除去
            if value.hasPrefix("\"") && value.hasSuffix("\"") {
                value = String(value.dropFirst().dropLast())
            } else if value.hasPrefix("'") && value.hasSuffix("'") {
                value = String(value.dropFirst().dropLast())
            }
            guard !key.isEmpty else { continue }
            result[key] = value
        }
        return result
    }

    /// 辞書を YAML 文字列に変換。
    static func serialize(_ dict: [String: String]) -> String {
        var lines: [String] = []
        for (key, value) in dict.sorted(by: { $0.key < $1.key }) {
            let escaped = value.contains(" ") ? "\"\(value)\"" : value
            lines.append("\(key): \(escaped)")
        }
        return lines.joined(separator: "\n") + "\n"
    }
}
