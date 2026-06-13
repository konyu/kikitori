import SwiftUI
import AppKit

// MARK: - Waveform Bar Model

@MainActor
final class WaveformModel: ObservableObject {
    @Published var levels: [Float] = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05,
                                       0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05,
                                       0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05]

    func push(_ amp: Float) {
        let clamped = min(max(amp, 0.01), 1.0)
        // 先頭に新しい値を追加、末尾を削除
        var new = levels
        new.append(clamped)
        new.removeFirst()
        levels = new
    }
}

// MARK: - View

struct OverlayView: View {
    @ObservedObject var model: WaveformModel

    var body: some View {
        HStack(spacing: 2) {
            ForEach(0..<model.levels.count, id: \.self) { i in
                RoundedRectangle(cornerRadius: 1)
                    .fill(.white.opacity(0.9))
                    .frame(width: 2, height: CGFloat(model.levels[i]) * 28 + 2)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(
            Capsule()
                .fill(.black.opacity(0.85))
        )
    }
}

// MARK: - Controller

@MainActor
final class OverlayController: NSObject {
    private var window: NSWindow?
    private var hosting: NSHostingView<OverlayView>?
    private let model = WaveformModel()

    func show() {
        guard window == nil else { return }

        let view = OverlayView(model: model)
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

    func updateAmplitude(_ amp: Float) {
        model.push(amp)
    }
}
