import SwiftUI
import AppKit

// MARK: - View

struct OverlayView: View {
    @State private var pulse = false

    var body: some View {
        HStack(spacing: 10) {
            // 録音インジケーター（パルスする赤丸）
            Circle()
                .fill(.red)
                .frame(width: 8, height: 8)
                .scaleEffect(pulse ? 1.3 : 0.7)
                .opacity(pulse ? 1.0 : 0.4)

            Text("入力中...")
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(.white.opacity(0.9))
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(
            Capsule()
                .fill(.black.opacity(0.85))
        )
        .onAppear {
            withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
                pulse = true
            }
        }
    }
}

// MARK: - Controller

@MainActor
final class OverlayController: NSObject {
    private var window: NSWindow?
    private var hosting: NSHostingView<OverlayView>?

    func show() {
        guard window == nil else { return }

        let view = OverlayView()
        let hosting = NSHostingView(rootView: view)
        self.hosting = hosting
        hosting.frame.size = hosting.fittingSize
        let size = hosting.fittingSize

        guard let screen = NSScreen.main else { return }
        let screenFrame = screen.visibleFrame
        let x = screenFrame.midX - size.width / 2
        let y = screenFrame.minY + screenFrame.height * 0.15 - size.height / 2

        let win = NSWindow(
            contentRect: NSRect(origin: CGPoint(x: x, y: y), size: size),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        win.isOpaque = false
        win.backgroundColor = .clear
        win.level = .floating
        win.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        win.ignoresMouseEvents = true
        win.contentView = hosting
        win.makeKeyAndOrderFront(nil)
        self.window = win
    }

    func hide() {
        window?.orderOut(nil)
        window = nil
        hosting = nil
    }
}
