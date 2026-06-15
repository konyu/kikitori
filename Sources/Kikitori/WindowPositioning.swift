import AppKit

extension NSWindow {
    /// ウィンドウをメインスクリーンの中央に配置する。
    /// ウィンドウサイズが確定していない場合（defer: true など）でも、
    /// 指定したコンテンツサイズからフレームを計算して中央に配置する。
    func center(withContentSize contentSize: NSSize) {
        guard let screen = self.screen ?? NSScreen.main else { return }

        let contentRect = NSRect(origin: .zero, size: contentSize)
        let frame = self.frameRect(forContentRect: contentRect)
        let screenFrame = screen.visibleFrame

        let x = screenFrame.midX - frame.width / 2
        let y = screenFrame.midY - frame.height / 2

        self.setFrame(
            NSRect(origin: CGPoint(x: x, y: y), size: frame.size),
            display: false,
            animate: false
        )
    }
}
