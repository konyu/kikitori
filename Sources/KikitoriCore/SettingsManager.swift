import Foundation

/// 設定ファイル（~/.kikitori/settings.yaml）の読み書きを管理する。
public final class SettingsManager: @unchecked Sendable {
    /// 設定ファイルのデフォルトパス
    public static let defaultPath: URL = {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".kikitori")
            .appendingPathComponent("settings.yaml")
    }()

    private let fileURL: URL
    private let lock = NSLock()

    // MARK: - 設定値（デフォルト値付き）

    /// 認識言語（例: "ja", "en"）
    public private(set) var language: String = "ja"

    /// UI 言語（"ja" or "en"）。nil の場合は OS から自動検出。
    public private(set) var uiLanguage: String? = nil

    /// ホットキー名の配列（例: ["option"], ["ctrl", "shift"], ["f13"]）
    public private(set) var hotkey: [String] = ["option"]

    /// 最低録音時間（ミリ秒）
    public private(set) var minDurationMs: Int = 300

    /// 最大録音時間（秒）
    public private(set) var maxDurationSec: Int = 60

    /// 無音判定 RMS 閾値（0 で無効）
    public private(set) var silenceRmsThreshold: Double = 0.0001

    /// デバッグログ有効フラグ
    public private(set) var debug: Bool = false

    // MARK: - 初期化

    public init(path: URL? = nil) {
        self.fileURL = path ?? Self.defaultPath
    }

    // MARK: - ファイル操作

    /// 設定ファイルを読み込み、プロパティを上書きする。
    /// ファイルが存在しない場合はデフォルト値のまま。
    public func load() {
        lock.withLock {
            _load()
        }
    }

    /// 現在の設定値をファイルに保存する。
    public func save() {
        lock.withLock {
            _save()
        }
    }

    /// 設定ファイルを削除し、全プロパティをデフォルトに戻す。
    public func reset() {
        lock.withLock {
            try? FileManager.default.removeItem(at: fileURL)
            _resetProperties()
        }
    }

    // MARK: - 内部実装

    private func _load() {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
        guard let text = try? String(contentsOf: fileURL, encoding: .utf8) else { return }
        let dict = SimpleYAML.parse(text)
        guard !dict.isEmpty else { return }

        if let v = dict["language"] { language = v }
        if let v = dict["ui_language"] { uiLanguage = v.isEmpty ? nil : v }
        if let v = dict["hotkey"] {
            // "option" → ["option"]、カンマ区切り "ctrl, shift" → ["ctrl", "shift"]
            let parts = v.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
            hotkey = parts.isEmpty ? ["option"] : parts
        }
        if let v = dict["min_duration_ms"], let n = Int(v) { minDurationMs = n }
        if let v = dict["max_duration_sec"], let n = Int(v) { maxDurationSec = n }
        if let v = dict["silence_rms_threshold"], let d = Double(v) { silenceRmsThreshold = d }
        if let v = dict["debug"] { debug = v == "true" || v == "1" || v == "yes" }
    }

    private func _save() {
        let dict: [String: String] = [
            "language": language,
            "ui_language": uiLanguage ?? "",
            "hotkey": hotkey.joined(separator: ", "),
            "min_duration_ms": String(minDurationMs),
            "max_duration_sec": String(maxDurationSec),
            "silence_rms_threshold": String(silenceRmsThreshold),
            "debug": debug ? "true" : "false",
        ]
        let yaml = SimpleYAML.serialize(dict)

        // 親ディレクトリ作成
        let dir = fileURL.deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

        // テンポラリファイル → リネームでアトミック書き込み
        let tempURL = dir.appendingPathComponent(".settings_tmp.yaml")
        try? yaml.write(to: tempURL, atomically: false, encoding: .utf8)
        try? FileManager.default.replaceItem(at: fileURL, withItemAt: tempURL, backupItemName: nil, resultingItemURL: nil)
    }

    private func _resetProperties() {
        language = "ja"
        uiLanguage = nil
        hotkey = ["option"]
        minDurationMs = 300
        maxDurationSec = 60
        silenceRmsThreshold = 0.0001
        debug = false
    }
}
