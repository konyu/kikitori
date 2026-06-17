import SwiftUI
import AppKit

// MARK: - Waveform Bar Model

@MainActor
final class WaveformModel: ObservableObject {
    @Published var levels: [Float] = Array(repeating: 0.05, count: 12)

    func push(_ amp: Float) {
        let boosted = sqrt(amp) * 3.5
        let clamped = min(max(boosted, 0.05), 1.0)

        var newLevels: [Float] = []
        for i in 0..<12 {
            // 中央が一番高く、端に行くほど低くなる係数 (0.3 〜 1.0)
            let centerBias = 1.0 - (abs(Float(i) - 5.5) / 5.5) * 0.7

            // 声が出ている時だけ各バーにランダムな揺らぎを加える
            let noise = clamped > 0.1 ? Float.random(in: 0.6...1.4) : 1.0

            let val = clamped * centerBias * noise
            newLevels.append(val)
        }
        levels = newLevels
    }
}

// MARK: - View

struct OverlayView: View {
    @ObservedObject var model: WaveformModel

    var body: some View {
        HStack(spacing: 14) {
            // アイコン
            if let img = IconLoader.loadIdleIcon() {
                Image(nsImage: img)
                    .resizable()
                    .renderingMode(.template)
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 22, height: 22)
                    .foregroundColor(Color(red: 84/255, green: 164/255, blue: 255/255))
            } else {
                Circle()
                    .fill(Color(red: 84/255, green: 164/255, blue: 255/255))
                    .frame(width: 26, height: 26)
            }

            // 12本の波形バー
            HStack(spacing: 4) {
                ForEach(0..<model.levels.count, id: \.self) { i in
                    let level = model.levels[i]
                    let h = max(4.0, CGFloat(level) * 30.0)

                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color(red: 160/255, green: 175/255, blue: 190/255))
                        .frame(width: 4, height: min(h, 24)) // 以前と同じぐらいの高さ制限
                }
            }
            // 流れるのをやめ、その場で滑らかに波打つアニメーション
            .animation(.interactiveSpring(response: 0.15, dampingFraction: 0.6, blendDuration: 0.1), value: model.levels)
        }
        .padding(.horizontal, 24)
        .frame(height: 44) // 全体の高さを元に戻す
        // Apple Liquid Glassデザイン (薄いマテリアル＋暗いオーバーレイ＋エッジハイライト＋シャドウ)
        .background(
            Capsule()
                .fill(.ultraThinMaterial)
                .overlay(
                    Capsule()
                        .fill(Color.black.opacity(0.3))
                )
                .overlay(
                    Capsule()
                        .stroke(Color.white.opacity(0.15), lineWidth: 0.5)
                )
                .shadow(color: Color.black.opacity(0.3), radius: 12, x: 0, y: 6)
        )
        // 常にダーク系のガラス効果を強制する
        .preferredColorScheme(.dark)
        // シャドウがウィンドウの境界で不自然に切れるのを防ぐため、外側に十分な透明の余白を設ける
        .padding(30)
    }
}

// MARK: - Controller

@MainActor
final class OverlayController: NSObject {
    private var window: NSWindow?
    private var hostingController: NSHostingController<OverlayView>?
    private let model = WaveformModel()

    func show() {
        guard window == nil else { return }

        let view = OverlayView(model: model)
        let hosting = NSHostingController(rootView: view)
        // 背景を完全に透明にする（余白の白背景を防ぐ）
        hosting.view.wantsLayer = true
        hosting.view.layer?.backgroundColor = NSColor.clear.cgColor

        self.hostingController = hosting

        let size = hosting.view.fittingSize
        hosting.view.frame.size = size

        guard let screen = NSScreen.main else { return }
        let screenFrame = screen.visibleFrame
        let x = screenFrame.midX - size.width / 2
        // 少し上に浮かせる
        let y = screenFrame.minY + screenFrame.height * 0.15 - size.height / 2

        let win = NSWindow(
            contentRect: NSRect(origin: CGPoint(x: x, y: y), size: size),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        win.isOpaque = false
        win.backgroundColor = .clear
        win.hasShadow = false
        win.level = .floating
        win.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        win.ignoresMouseEvents = true
        win.contentViewController = hosting
        win.orderFrontRegardless()
        self.window = win
    }

    func hide() {
        window?.orderOut(nil)
        window = nil
        hostingController = nil
    }

    func updateAmplitude(_ amp: Float) {
        model.push(amp)
    }
}
