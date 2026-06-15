import Testing
import Foundation
@testable import KikitoriCore

struct CorrectionsTests {

    func tempPath() -> URL {
        let tmp = FileManager.default.temporaryDirectory
            .appendingPathComponent("kikitori-test-\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: tmp, withIntermediateDirectories: true)
        return tmp.appendingPathComponent("corrections.yaml")
    }

    func cleanup(_ path: URL) {
        try? FileManager.default.removeItem(at: path)
        try? FileManager.default.removeItem(at: path.deletingLastPathComponent())
    }

    @Test("空文字はそのまま")
    func testEmptyText() {
        let c = Corrections()
        c.setPairs([("use", "USE")])
        #expect(c.apply(to: "") == "")
    }

    @Test("ペアなしはそのまま")
    func testNoPairs() {
        let c = Corrections()
        #expect(c.apply(to: "hello") == "hello")
    }

    @Test("単純置換")
    func testSimpleReplacement() {
        let c = Corrections()
        c.setPairs([("foo", "bar")])
        #expect(c.apply(to: "foo") == "bar")
    }

    @Test("ケースインセンシティブ")
    func testCaseInsensitive() {
        let c = Corrections()
        c.setPairs([("hello", "HELLO")])
        #expect(c.apply(to: "Hello") == "HELLO")
        #expect(c.apply(to: "HELLO") == "HELLO")
        #expect(c.apply(to: "HeLLo") == "HELLO")
    }

    @Test("長いキー優先")
    func testLongestMatchFirst() {
        let c = Corrections()
        c.setPairs([
            ("use", "USE"),
            ("use effect", "useEffect"),
        ])
        #expect(c.apply(to: "use effect") == "useEffect")
    }

    @Test("非再帰置換")
    func testNonRecursive() {
        let c = Corrections()
        c.setPairs([("ab", "bc")])
        // "ab" → "bc"。置換後の "bc" が "ab" にマッチして再置換されない
        #expect(c.apply(to: "ab") == "bc")
    }

    @Test("文中の置換")
    func testInSentence() {
        let c = Corrections()
        c.setPairs([("world", "WORLD")])
        #expect(c.apply(to: "hello world again") == "hello WORLD again")
    }

    @Test("ファイル読み込み")
    func testLoadFromFile() throws {
        let path = tempPath()
        defer { cleanup(path) }

        let yaml = """
            corrections:
              use effect: useEffect
              use state: useState
            """
        try yaml.write(to: path, atomically: true, encoding: .utf8)

        let c = Corrections(path: path)
        c.load()
        let items = c.items
        #expect(items.count == 2)
        #expect(items.contains { $0.wrong == "use effect" && $0.right == "useEffect" })
        #expect(items.contains { $0.wrong == "use state" && $0.right == "useState" })
    }

    @Test("ファイル不在で空")
    func testLoadMissingFile() {
        let path = tempPath()
        // ファイルを作らない
        let c = Corrections(path: path)
        c.load()
        #expect(c.items.isEmpty)
        cleanup(path)
    }

    @Test("保存→再読み込みで一致")
    func testSaveAndReload() throws {
        let path = tempPath()
        defer { cleanup(path) }

        let c = Corrections(path: path)
        c.setPairs([("foo", "bar"), ("baz", "qux")])
        c.save()

        let c2 = Corrections(path: path)
        c2.load()
        #expect(c2.items.count == 2)
        #expect(c2.apply(to: "foo") == "bar")
    }
}
