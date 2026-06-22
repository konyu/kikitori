import AppKit
import SwiftUI
import KikitoriCore

public final class AccessibilityDialogManager: @unchecked Sendable {
    public static let shared = AccessibilityDialogManager()
    private var windowController: NSWindowController?
    
    private init() {}
    
    @MainActor
    public func show(transcribedText: String, i18n: I18n) {
        if UserDefaults.standard.bool(forKey: "hideAccessibilityDialog") {
            return
        }
        
        if windowController == nil {
            let view = AccessibilityDialogView(text: transcribedText, i18n: i18n) { [weak self] in
                self?.windowController?.close()
            }
            let host = NSHostingController(rootView: view)
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 450, height: 350),
                styleMask: [.titled, .closable, .fullSizeContentView],
                backing: .buffered,
                defer: false
            )
            window.titlebarAppearsTransparent = true
            window.titleVisibility = .hidden
            window.isMovableByWindowBackground = true
            window.contentViewController = host
            window.center()
            window.level = .floating
            windowController = NSWindowController(window: window)
        } else {
            if let host = windowController?.contentViewController as? NSHostingController<AccessibilityDialogView> {
                host.rootView = AccessibilityDialogView(text: transcribedText, i18n: i18n) { [weak self] in
                    self?.windowController?.close()
                }
            }
        }
        
        windowController?.showWindow(nil)
        windowController?.window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

struct AccessibilityDialogView: View {
    let text: String
    @ObservedObject var i18n: I18n
    let onClose: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top, spacing: 16) {
                Image(nsImage: NSImage(named: "AppIcon") ?? NSImage())
                    .resizable()
                    .frame(width: 50, height: 50)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                
                VStack(alignment: .leading, spacing: 8) {
                    Text(i18n.t(.axPermissionTitle))
                        .font(.headline)
                        .fontWeight(.bold)
                    
                    Text(i18n.t(.axPermissionMessage))
                        .font(.subheadline)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            
            VStack(alignment: .leading, spacing: 4) {
                Text(i18n.t(.axPermissionStep1))
                Text(i18n.t(.axPermissionStep2))
                Text(i18n.t(.axPermissionStep3))
            }
            .font(.caption)
            .foregroundColor(.secondary)
            .padding(.leading, 66)
            
            if !text.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("\"\(text)\"")
                        .font(.callout)
                        .italic()
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Color(NSColor.controlBackgroundColor))
                        .cornerRadius(8)
                    
                    Text(i18n.t(.axPermissionCopied))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.leading, 66)
            }
            
            Spacer()
            
            HStack {
                Button(i18n.t(.btnClose)) {
                    onClose()
                }
                .keyboardShortcut(.cancelAction)
                
                Button(i18n.t(.btnDoNotShowAgain)) {
                    UserDefaults.standard.set(true, forKey: "hideAccessibilityDialog")
                    onClose()
                }
                
                Spacer()
                
                Button(i18n.t(.permissionOpenSettings)) {
                    if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
                        NSWorkspace.shared.open(url)
                    }
                    onClose()
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
            .padding(.top, 8)
        }
        .padding(24)
        .frame(width: 450)
    }
}
