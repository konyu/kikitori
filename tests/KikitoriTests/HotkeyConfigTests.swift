import Testing
@testable import KikitoriCore

struct HotkeyConfigTests {

    @Test("option 文字列 → .option")
    func testParseOption() {
        let config = HotkeyConfig.parse(from: ["option"])
        #expect(config == .option)
    }

    @Test("空配列 → .modifiers([.fn])（デフォルト）")
    func testParseEmpty() {
        let config = HotkeyConfig.parse(from: [])
        #expect(config == .modifiers([.fn]))
    }

    @Test("未知キー名 → .modifiers([.fn]) にフォールバック")
    func testParseUnknown() {
        let config = HotkeyConfig.parse(from: ["unknown_key"])
        #expect(config == .modifiers([.fn]))
    }

    @Test("fn 修飾キー")
    func testParseFn() {
        let config = HotkeyConfig.parse(from: ["fn"])
        #expect(config == .modifiers([.fn]))
    }

    @Test("単一修飾キー: ctrl")
    func testParseCtrlOnly() {
        let config = HotkeyConfig.parse(from: ["ctrl"])
        #expect(config == .modifiers([.ctrl]))
    }

    @Test("複数修飾キー: ctrl + shift")
    func testParseMultiModifiers() {
        let config = HotkeyConfig.parse(from: ["ctrl", "shift"])
        #expect(config == .modifiers([.ctrl, .shift]))
    }

    @Test("cmd + space → .key")
    func testParseCmdSpace() {
        let config = HotkeyConfig.parse(from: ["cmd", "space"])
        #expect(config == .key(modifiers: [.cmd], keyCode: 49))
    }

    @Test("f13 単体 → .key（修飾なし）")
    func testParseF13() {
        let config = HotkeyConfig.parse(from: ["f13"])
        #expect(config == .key(modifiers: [], keyCode: 105))
    }

    @Test("f1 キーコード")
    func testParseF1() {
        let config = HotkeyConfig.parse(from: ["f1"])
        #expect(config == .key(modifiers: [], keyCode: 122))
    }

    @Test("a キー")
    func testParseA() {
        let config = HotkeyConfig.parse(from: ["a"])
        #expect(config == .key(modifiers: [], keyCode: 0))
    }

    @Test("z キー")
    func testParseZ() {
        let config = HotkeyConfig.parse(from: ["z"])
        #expect(config == .key(modifiers: [], keyCode: 25))
    }

    @Test("数字キー")
    func testParseDigits() {
        #expect(HotkeyConfig.parse(from: ["0"]) == .key(modifiers: [], keyCode: 29))
        #expect(HotkeyConfig.parse(from: ["1"]) == .key(modifiers: [], keyCode: 30))
        #expect(HotkeyConfig.parse(from: ["9"]) == .key(modifiers: [], keyCode: 38))
    }

    @Test("修飾 + 文字キー: cmd + shift + a")
    func testParseMultiModifiersWithKey() {
        let config = HotkeyConfig.parse(from: ["cmd", "shift", "a"])
        #expect(config == .key(modifiers: [.cmd, .shift], keyCode: 0))
    }

    @Test("Alt は alt 修飾キーにマップ")
    func testParseAlt() {
        let config = HotkeyConfig.parse(from: ["alt"])
        #expect(config == .modifiers([.alt]))
    }

    @Test("大文字小文字不感")
    func testCaseInsensitive() {
        let opt = HotkeyConfig.parse(from: ["Option"])
        #expect(opt == .option)

        let ctrl = HotkeyConfig.parse(from: ["CTRL"])
        #expect(ctrl == .modifiers([.ctrl]))

        let f = HotkeyConfig.parse(from: ["F5"])
        #expect(f == .key(modifiers: [], keyCode: 96))
    }
}
