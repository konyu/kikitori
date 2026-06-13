import Testing
import KikitoriCore

struct DebugLoggerTests {
    @Test("初期状態は disabled")
    func testDefaultDisabled() {
        let logger = DebugLogger()
        #expect(logger.enabled == false)
        // log() は何も出力せずクラッシュしない（NSLog 出力は検証不可）
        logger.log("should not be printed")
    }

    @Test("enabled の切り替え")
    func testToggle() {
        let logger = DebugLogger()
        logger.enabled = true
        #expect(logger.enabled == true)
        logger.log("should be printed")

        logger.enabled = false
        #expect(logger.enabled == false)
    }

    @Test("autoclosure は enabled 時のみ評価される")
    func testAutoclosureEvaluatedOnlyWhenEnabled() {
        let logger = DebugLogger()
        var called = false
        logger.log({ called = true; return "hi" }())
        #expect(called == false)  // enabled=false → autoclosure 未評価

        logger.enabled = true
        logger.log({ called = true; return "hi" }())
        #expect(called == true)   // enabled=true → autoclosure 評価
    }

    @Test("shared インスタンスが同一")
    func testSharedSingleton() {
        let a = DebugLogger.shared
        let b = DebugLogger.shared
        #expect(a === b)
    }
}
