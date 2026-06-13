import Testing
import KikitoriCore

struct FrontmostAppTrackerTests {

    @Test("初期状態で currentPID は nil")
    func testInitialPIDIsNil() {
        let tracker = FrontmostAppTracker()
        #expect(tracker.currentPID == nil)
    }

    @Test("capture() が PID を返す")
    func testCaptureReturnsPID() {
        let tracker = FrontmostAppTracker()
        let pid = tracker.capture()
        // テスト実行中は必ず何らかのアプリが最前面にある
        #expect(pid != nil)
        #expect(pid! > 0)
        #expect(tracker.currentPID == pid)
    }

    @Test("restore() が capture() なしでクラッシュしない")
    func testRestoreWithoutCapture() {
        let tracker = FrontmostAppTracker()
        // クラッシュしないことだけ確認
        tracker.restore()
    }
}
