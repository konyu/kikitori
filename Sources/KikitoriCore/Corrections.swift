import Foundation

/// 校正辞書。認識結果テキストにユーザー定義の置換を適用する。
///
/// ファイル: ~/.kikitori/corrections.yaml
/// フォーマット:
///   corrections:
///     "use effect": "useEffect"
///     "use state": "useState"
public final class Corrections: @unchecked Sendable {
    public static let defaultPath: URL = {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".kikitori")
            .appendingPathComponent("corrections.yaml")
    }()

    private let fileURL: URL
    private let lock = NSLock()
    private var pairs: [(wrong: String, right: String)] = []

    public init(path: URL? = nil) {
        self.fileURL = path ?? Self.defaultPath
    }

    /// 校正ペアを読み込む。ファイル不在時は空。
    public func load() {
        lock.withLock { _load() }
    }

    /// 現在のペアをファイルに保存。
    public func save() {
        lock.withLock { _save() }
    }

    /// ペア一覧を取得（テスト用）。
    public var items: [(wrong: String, right: String)] {
        lock.withLock { pairs }
    }

    /// テキストに校正を適用する。
    ///
    /// アルゴリズム:
    /// 1. wrong の長い順にソート（"use effect" が "use" より先）
    /// 2. ケースインセンシティブマッチ
    /// 3. 非再帰置換（一度置換した文字は再検査しない）
    /// 4. マッチしなければ 1 文字進む
    public func apply(to text: String) -> String {
        let sorted: [(wrong: String, right: String)] = lock.withLock {
            pairs.sorted { $0.wrong.count > $1.wrong.count }
        }
        guard !sorted.isEmpty, !text.isEmpty else { return text }

        var result = ""
        var i = text.startIndex
        while i < text.endIndex {
            var matched = false
            for (wrong, right) in sorted {
                let end = text.index(i, offsetBy: wrong.count, limitedBy: text.endIndex)
                if let end, text[i..<end].lowercased() == wrong.lowercased() {
                    result += right
                    i = end
                    matched = true
                    break
                }
            }
            if !matched {
                result.append(text[i])
                i = text.index(after: i)
            }
        }
        return result
    }

    /// ペアを置き換えて保存（GUI 用、後日）。
    public func setPairs(_ newPairs: [(wrong: String, right: String)]) {
        lock.withLock { pairs = newPairs }
    }

    // MARK: - 内部

    private func _load() {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
        guard let text = try? String(contentsOf: fileURL, encoding: .utf8) else { return }
        let dict = SimpleYAML.parse(text)
        var result: [(String, String)] = []
        result.reserveCapacity(dict.count)
        for (key, value) in dict {
            guard !key.isEmpty, !value.isEmpty, key != "corrections" else { continue }
            result.append((key, value))
        }
        pairs = result
    }

    private func _save() {
        var dict: [String: String] = [:]
        for (wrong, right) in pairs {
            dict[wrong] = right
        }
        let yaml = SimpleYAML.serialize(dict)

        let dir = fileURL.deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try? yaml.write(to: fileURL, atomically: true, encoding: .utf8)
    }
}
