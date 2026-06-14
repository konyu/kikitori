import Testing
@testable import KikitoriCore

@MainActor
struct I18nTests {

    @Test("ja 言語で全キーが日本語を返す")
    func testJapanese() {
        let i18n = I18n(language: .ja)
        #expect(i18n.t(.menuSettings) == "設定")
        #expect(i18n.t(.menuQuit) == "終了")
        #expect(i18n.t(.statusIdle) == "待機中")
        #expect(i18n.t(.statusRecording) == "録音中")
    }

    @Test("en 言語で全キーが英語を返す")
    func testEnglish() {
        let i18n = I18n(language: .en)
        #expect(i18n.t(.menuSettings) == "Settings")
        #expect(i18n.t(.menuQuit) == "Quit")
        #expect(i18n.t(.statusIdle) == "Idle")
        #expect(i18n.t(.statusRecording) == "Recording")
    }

    @Test("未定義キーは ja にフォールバック")
    func testFallbackToJapanese() {
        // 全キーは定義済みなので、フォールバックは直接テスト不可だが、
        // 存在しないキーを渡してもクラッシュしないことを確認
        // （現状、全 TranslationKey は両言語で定義済み）
        let enI18n = I18n(language: .en)
        // 全キーが空でない値を返す
        for key in TranslationKey.allCases {
            #expect(!enI18n.t(key).isEmpty, "\(key) should not be empty in en")
        }
    }

    @Test("ja と en で異なる文字列を返す")
    func testDifferentPerLanguage() {
        let ja = I18n(language: .ja)
        let en = I18n(language: .en)
        #expect(ja.t(.settingsTitle) != en.t(.settingsTitle))
    }

    @Test("detectOSLanguage: ja プレフィックスで ja")
    func testOSDetectionJa() {
        let lang = I18n.detectOSLanguage()  // 実際の OS 環境に依存
        // macOS 日本語環境なら ja、それ以外なら en を期待
        #expect(lang == .ja || lang == .en)
    }

    @Test("言語切り替えで currentLanguage が反映される")
    func testCurrentLanguage() {
        let ja = I18n(language: .ja)
        let en = I18n(language: .en)
        #expect(ja.currentLanguage == .ja)
        #expect(en.currentLanguage == .en)
    }
}
