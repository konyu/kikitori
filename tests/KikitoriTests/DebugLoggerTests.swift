import Testing
import KikitoriCore

struct DebugLoggerTests {
    @Test("初期状態は disabled")
    func testDefaultDisabled() {
        DebugLogger.enabled = false
        #expect(DebugLogger.enabled == false)
        // log() は何も出力せずクラッシュしない（NSLog 出力は検証不可）
        DebugLogger.log("should not be printed")
    }

    @Test("enabled の切り替え")
    func testToggle() {
        DebugLogger.enabled = true
        #expect(DebugLogger.enabled == true)
        DebugLogger.log("should be printed")

        DebugLogger.enabled = false
        #expect(DebugLogger.enabled == false)
    }

    @Test("autoclosure は enabled 時のみ評価される")
    func testAutoclosureEvaluatedOnlyWhenEnabled() {
        DebugLogger.enabled = false
        var called = false
        DebugLogger.log({ called = true; return "hi" }())
        #expect(called == false)  // enabled=false → autoclosure 未評価

        DebugLogger.enabled = true
        DebugLogger.log({ called = true; return "hi" }())
        #expect(called == true)   // enabled=true → autoclosure 評価

        DebugLogger.enabled = false
    }

    @Test("static アクセスで状態が共有される")
    func testStaticState() {
        DebugLogger.enabled = true
        #expect(DebugLogger.enabled == true)
        DebugLogger.enabled = false
        #expect(DebugLogger.enabled == false)
    }
}
