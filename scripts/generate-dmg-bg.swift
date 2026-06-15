#!/usr/bin/swift

import Cocoa

func createDMGBackground(outputPath: String) {
    let size = CGSize(width: 600, height: 400)
    let image = NSImage(size: size)
    
    image.lockFocus()
    
    // 背景: やや明るいグラデーション
    guard let context = NSGraphicsContext.current?.cgContext else { return }
    let colors = [
        NSColor(white: 0.95, alpha: 1.0).cgColor,
        NSColor(white: 0.88, alpha: 1.0).cgColor
    ]
    let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: colors as CFArray, locations: [0.0, 1.0])!
    context.drawLinearGradient(gradient, start: CGPoint(x: 0, y: size.height), end: CGPoint(x: 0, y: 0), options: [])
    
    // 矢印を描画
    context.setStrokeColor(NSColor(white: 0.7, alpha: 1.0).cgColor)
    context.setLineWidth(4.0)
    context.setLineDash(phase: 0, lengths: [8.0, 6.0])
    
    context.move(to: CGPoint(x: 240, y: 200))
    context.addLine(to: CGPoint(x: 360, y: 200))
    context.strokePath()
    
    // 矢印の先端
    context.setLineDash(phase: 0, lengths: [])
    context.move(to: CGPoint(x: 350, y: 210))
    context.addLine(to: CGPoint(x: 365, y: 200))
    context.addLine(to: CGPoint(x: 350, y: 190))
    context.strokePath()
    
    // テキストを描画（英語と日本語併記）
    let paragraphStyle = NSMutableParagraphStyle()
    paragraphStyle.alignment = .center
    
    let attrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: 24, weight: .semibold),
        .foregroundColor: NSColor(white: 0.4, alpha: 1.0),
        .paragraphStyle: paragraphStyle
    ]
    
    let subAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: 14, weight: .regular),
        .foregroundColor: NSColor(white: 0.5, alpha: 1.0),
        .paragraphStyle: paragraphStyle
    ]
    
    // 上部のタイトル
    let title = "Install Kikitori"
    let titleRect = CGRect(x: 0, y: 320, width: size.width, height: 40)
    title.draw(in: titleRect, withAttributes: attrs)
    
    // 下部の指示（日本語）
    let jaText = "左のアイコンを右の Applications フォルダにドラッグ＆ドロップしてください。"
    let jaRect = CGRect(x: 0, y: 80, width: size.width, height: 30)
    jaText.draw(in: jaRect, withAttributes: subAttrs)
    
    // 下部の指示（英語）
    let enText = "Drag the icon on the left to the Applications folder on the right."
    let enRect = CGRect(x: 0, y: 50, width: size.width, height: 30)
    enText.draw(in: enRect, withAttributes: subAttrs)
    
    image.unlockFocus()
    
    // PNGとして保存
    if let tiffData = image.tiffRepresentation,
       let bitmapImage = NSBitmapImageRep(data: tiffData),
       let pngData = bitmapImage.representation(using: .png, properties: [:]) {
        try? pngData.write(to: URL(fileURLWithPath: outputPath))
        print("Generated DMG background: \(outputPath)")
    }
}

let args = CommandLine.arguments
if args.count > 1 {
    createDMGBackground(outputPath: args[1])
} else {
    print("Usage: ./generate-dmg-bg.swift <output.png>")
}
