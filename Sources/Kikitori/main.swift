import AppKit
let a = NSApplication.shared
a.setActivationPolicy(.accessory)
a.delegate = AppDelegate()
a.run()
