import AppKit

let args = CommandLine.arguments
if args.contains("--version") || args.contains("-v") {
    print("Kikitori 0.8.0")
    exit(0)
}

let a = NSApplication.shared
a.setActivationPolicy(.accessory)
let delegate = AppDelegate()
a.delegate = delegate
a.run()
