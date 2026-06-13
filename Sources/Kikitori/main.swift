import AppKit

let args = CommandLine.arguments
if args.contains("--version") || args.contains("-v") {
    print("Kikitori 0.8.0")
    exit(0)
}

let a = NSApplication.shared
a.setActivationPolicy(.accessory)
a.delegate = AppDelegate()
a.run()
