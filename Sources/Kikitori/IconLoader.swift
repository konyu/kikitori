import AppKit

enum IconLoader {
    static func loadIdleIcon() -> NSImage? {
        // 1. 配布用 .app では Contents/Resources 直下の PNG を読み込み
        //    （SPM リソースバンドルがルートに無くてもこちらが使われる）
        if let path = Bundle.main.path(forResource: "icon-idle", ofType: "png"),
           let img = NSImage(contentsOfFile: path) {
            img.isTemplate = true
            return img
        }

        #if SWIFT_PACKAGE
        // 2. 開発時 (swift run) は SPM リソースバンドルから読み込み
        if let img = Bundle.module.image(forResource: "icon-idle") {
            img.isTemplate = true
            return img
        }
        #endif

        // 3. フォールバック
        return NSImage(systemSymbolName: "mic", accessibilityDescription: "Kikitori")
    }
}
