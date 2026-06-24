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
    /// 最初に日本語テキストの正規化（句読点前のスペース除去）を行い、
    /// その後ユーザー定義の置換を適用する。
    ///
    /// アルゴリズム:
    /// 1. 日本語正規化（句読点前のスペース除去）
    /// 2. wrong の長い順にソート（"use effect" が "use" より先）
    /// 3. ケースインセンシティブマッチ
    /// 4. 非再帰置換（一度置換した文字は再検査しない）
    /// 5. マッチしなければ 1 文字進む
    public func apply(to text: String) -> String {
        guard !text.isEmpty else { return text }

        // 日本語正規化: 句読点前のASCIIスペースを除去
        let normalized = Self.normalizeJapanese(text)

        let sorted: [(wrong: String, right: String)] = lock.withLock {
            pairs.sorted { $0.wrong.count > $1.wrong.count }
        }
        guard !sorted.isEmpty else { return normalized }

        var result = ""
        var i = normalized.startIndex
        while i < normalized.endIndex {
            var matched = false
            for (wrong, right) in sorted {
                let end = normalized.index(i, offsetBy: wrong.count, limitedBy: normalized.endIndex)
                if let end, normalized[i..<end].lowercased() == wrong.lowercased() {
                    result += right
                    i = end
                    matched = true
                    break
                }
            }
            if !matched {
                result.append(normalized[i])
                i = normalized.index(after: i)
            }
        }
        return result
    }

    /// 日本語テキストの正規化: 句読点前のASCIIスペースを除去する。
    /// e.g. "あの件どうなりましたか ？" → "あの件どうなりましたか？"
    public static func normalizeJapanese(_ text: String) -> String {
        // CJK句読点 + 全角記号（前にスペースを入れてはいけない文字）
        // U+3001(、) U+3002(。) U+FF1F(？) U+FF01(！)
        // U+300D(」) U+300F(』) U+FF09(）) U+3011(】)
        // U+FF5D(｝) U+3009(〉) U+300B(》) U+301F(〟)
        let pattern = " +(?=[、。？！！」』）】｝〉》〟])"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            return text
        }
        let range = NSRange(text.startIndex..<text.endIndex, in: text)
        return regex.stringByReplacingMatches(in: text, options: [], range: range, withTemplate: "")
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
