import Foundation
@preconcurrency import AVFoundation
import Speech

/// マイク音声キャプチャ。専用キューで AVAudioEngine を操作。
public final class AudioCapture: @unchecked Sendable {
    private let engine = AVAudioEngine()
    private let queue = DispatchQueue(label: "com.kikitori.audio")
    
    public var targetFormat: AVAudioFormat?
    public var onAudioBuffer: ((AVAudioPCMBuffer) -> Void)?
    
    public init() {}
    
    public func start() async throws {
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            queue.async {
                do {
                    let input = self.engine.inputNode
                    let inputFmt = input.outputFormat(forBus: 0)
                    input.installTap(onBus: 0, bufferSize: 4096, format: inputFmt) { [weak self] buf, _ in
                        self?.deliver(buf, from: inputFmt)
                    }
                    self.engine.prepare()
                    try self.engine.start()
                    cont.resume()
                } catch {
                    cont.resume(throwing: error)
                }
            }
        }
    }
    
    public func stop() {
        queue.sync {
            engine.inputNode.removeTap(onBus: 0)
            engine.stop()
        }
    }
    
    private func deliver(_ buffer: AVAudioPCMBuffer, from inputFmt: AVAudioFormat) {
        if let target = targetFormat {
            guard let cvt = AVAudioConverter(from: inputFmt, to: target) else { return }
            let outFrames = AVAudioFrameCount(Double(buffer.frameLength) * target.sampleRate / inputFmt.sampleRate)
            guard let out = AVAudioPCMBuffer(pcmFormat: target, frameCapacity: outFrames) else { return }
            var err: NSError?
            cvt.convert(to: out, error: &err) { _, s in s.pointee = .haveData; return buffer }
            if err == nil, out.frameLength > 0 { onAudioBuffer?(out) }
        } else {
            onAudioBuffer?(buffer)
        }
    }
}
