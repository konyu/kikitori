import Testing
import Foundation
@testable import KikitoriCore

struct SettingsManagerTests {
    /// テスト用一時ディレクトリを作成
    func tempSettingsPath() -> URL {
        let tmp = FileManager.default.temporaryDirectory
            .appendingPathComponent("kikitori-test-\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: tmp, withIntermediateDirectories: true)
        return tmp.appendingPathComponent("settings.yaml")
    }

    /// テスト後に一時ファイルを削除
    func cleanup(_ path: URL) {
        try? FileManager.default.removeItem(at: path)
        try? FileManager.default.removeItem(at: path.deletingLastPathComponent())
    }

    @Test("ファイル不在時はデフォルト値")
    func testDefaultsWhenNoFile() {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        let manager = SettingsManager(path: path)
        manager.load()

        #expect(manager.language == "ja")
        #expect(manager.uiLanguage == nil)
        #expect(manager.hotkey == ["fn"])
        #expect(manager.minDurationMs == 300)
        #expect(manager.maxDurationSec == 60)
        #expect(manager.silenceRmsThreshold == 0.0001)
        #expect(manager.debug == false)
    }

    @Test("全キー読み込み")
    func testLoadAllKeys() throws {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        let yaml = """
            language: en
            ui_language: en
            hotkey: ctrl, shift
            min_duration_ms: 500
            max_duration_sec: 120
            silence_rms_threshold: 0.01
            debug: true
            """
        try yaml.write(to: path, atomically: true, encoding: .utf8)

        let manager = SettingsManager(path: path)
        manager.load()

        #expect(manager.language == "en")
        #expect(manager.uiLanguage == "en")
        #expect(manager.hotkey == ["ctrl", "shift"])
        #expect(manager.minDurationMs == 500)
        #expect(manager.maxDurationSec == 120)
        #expect(manager.silenceRmsThreshold == 0.01)
        #expect(manager.debug == true)
    }

    @Test("部分的なキーのみ読み込み（他はデフォルト）")
    func testLoadPartialKeys() throws {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        let yaml = """
            language: zh
            min_duration_ms: 100
            """
        try yaml.write(to: path, atomically: true, encoding: .utf8)

        let manager = SettingsManager(path: path)
        manager.load()

        #expect(manager.language == "zh")
        #expect(manager.minDurationMs == 100)
        // 未指定キーはデフォルト
        #expect(manager.uiLanguage == nil)
        #expect(manager.hotkey == ["fn"])
        #expect(manager.maxDurationSec == 60)
    }

    @Test("保存→再読み込みで値一致")
    func testSaveAndReload() throws {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        let manager = SettingsManager(path: path)
        manager.load()
        // デフォルト値をそのまま save → reload
        manager.save()

        let manager2 = SettingsManager(path: path)
        manager2.load()

        #expect(manager2.language == "ja")
        #expect(manager2.hotkey == ["fn"])
        #expect(manager2.minDurationMs == 300)
        #expect(manager2.debug == false)
    }

    @Test("コメント行と空行を無視してパース")
    func testCommentsAndBlankLines() throws {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        let yaml = """
            # Kikitori settings
            language: en

            min_duration_ms: 1000
            # debug: true ← コメントアウト
            """
        try yaml.write(to: path, atomically: true, encoding: .utf8)

        let manager = SettingsManager(path: path)
        manager.load()

        #expect(manager.language == "en")
        #expect(manager.minDurationMs == 1000)
        #expect(manager.debug == false)  // コメント行の debug は無視
    }

    @Test("reset() でファイル削除とデフォルト値")
    func testReset() throws {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        // まず保存
        let manager = SettingsManager(path: path)
        manager.load()
        manager.save()
        #expect(FileManager.default.fileExists(atPath: path.path))

        // リセット
        manager.reset()

        #expect(!FileManager.default.fileExists(atPath: path.path))
        #expect(manager.language == "ja")
        #expect(manager.uiLanguage == nil)
        #expect(manager.hotkey == ["fn"])
        #expect(manager.minDurationMs == 300)
        #expect(manager.maxDurationSec == 60)
        #expect(manager.silenceRmsThreshold == 0.0001)
        #expect(manager.debug == false)
    }

    @Test("debug の true/false/1/yes パース")
    func testDebugParse() throws {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        let testCases: [(String, Bool)] = [
            ("true", true), ("1", true), ("yes", true),
            ("false", false), ("0", false), ("no", false),
        ]

        for (value, expected) in testCases {
            let yaml = "debug: \(value)"
            try yaml.write(to: path, atomically: true, encoding: .utf8)

            let manager = SettingsManager(path: path)
            manager.load()
            #expect(manager.debug == expected, "debug: \(value) → \(expected)")
        }
    }

    @Test("hotkey パース: 単一キーと複数キー")
    func testHotkeyParse() throws {
        let path = tempSettingsPath()
        defer { cleanup(path) }

        let testCases: [(String, [String])] = [
            ("option", ["option"]),
            ("ctrl, shift", ["ctrl", "shift"]),
            ("f13", ["f13"]),
            ("cmd, space", ["cmd", "space"]),
        ]

        for (yamlValue, expected) in testCases {
            let yaml = "hotkey: \(yamlValue)"
            try yaml.write(to: path, atomically: true, encoding: .utf8)

            let manager = SettingsManager(path: path)
            manager.load()
            #expect(manager.hotkey == expected, "hotkey: \(yamlValue) → \(expected)")
        }
    }
}
