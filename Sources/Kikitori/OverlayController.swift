import SwiftUI

// MARK: - View

struct OverlayView: View {
    @State private var opacityLow = true
    var amplitude: Float = 0.3

    var body: some View {
        VStack(spacing: 8) {
            ZStack {
                Circle()
                    .stroke(.white.opacity(0.2), lineWidth: 3)
                    .frame(width: 32, height: 32)
                Circle()
                    .stroke(.red, lineWidth: 2)
                    .frame(width: 24, height: 24)
                    .opacity(opacityLow ? 0.3 : 1.0)
                    .scaleEffect(opacityLow ? 0.7 : 1.0)
                Circle()
                    .fill(.red)
                    .frame(width: 6, height: 6)
            }

            Text("Recording...")
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.primary.opacity(0.7))
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(.ultraThinMaterial)
        )
        .onAppear {
            withAnimation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true)) {
                opacityLow = false
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

        let win = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 120, height: 80),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        win.isOpaque = false
        win.backgroundColor = .clear
        win.level = .floating
        win.collectionBehavior = [.canJoinAllSpaces, .stationary]
        win.ignoresMouseEvents = true
        win.contentView = hosting
        win.center()
        win.makeKeyAndOrderFront(nil)
        self.window = win
    }

    func hide() {
        window?.orderOut(nil)
        window = nil
        hosting = nil
    }

    func updateAmplitude(_ amp: Float) {
        guard let h = hosting else { return }
        h.rootView = OverlayView(amplitude: amp)
    }
}
