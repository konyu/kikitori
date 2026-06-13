import Testing
import KikitoriCore

@Test func hotkeyInit() {
    let h = HotkeyManager()
    #expect(h.onKeyDown == nil)
    #expect(h.onKeyUp == nil)
}
