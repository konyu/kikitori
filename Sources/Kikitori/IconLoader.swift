import AppKit

enum IconLoader {
    static func loadIdleIcon() -> NSImage? {
        #if SWIFT_PACKAGE
        if let img = Bundle.module.image(forResource: "icon-idle") {
            img.isTemplate = true
            return img
        }
        #endif
        return NSImage(systemSymbolName: "mic", accessibilityDescription: "Kikitori")
    }
}
