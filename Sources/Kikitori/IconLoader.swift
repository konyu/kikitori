import AppKit

enum IconLoader {
    static func loadIdleIcon() -> NSImage? {
        #if SWIFT_PACKAGE
        if let img = Bundle.module.image(forResource: "icon-idle") {
            img.isTemplate = true
            return img
        }
        #endif
        
        let possiblePaths = [
            "Sources/Kikitori/Resources/icon-idle.png",
            "../Sources/Kikitori/Resources/icon-idle.png",
            Bundle.main.resourcePath?.appending("/icon-idle.png")
        ]
        
        for path in possiblePaths {
            guard let path = path else { continue }
            if FileManager.default.fileExists(atPath: path), let img = NSImage(contentsOfFile: path) {
                img.isTemplate = true
                return img
            }
        }
        
        // Compile-time path fallback
        let compileTimePath = URL(fileURLWithPath: #file)
            .deletingLastPathComponent()
            .appendingPathComponent("Resources/icon-idle.png")
            .path
            
        if FileManager.default.fileExists(atPath: compileTimePath), let img = NSImage(contentsOfFile: compileTimePath) {
            img.isTemplate = true
            return img
        }
        
        return nil
    }
}
