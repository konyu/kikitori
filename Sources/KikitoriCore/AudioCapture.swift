import Foundation
@preconcurrency import AVFoundation
import Speech

/// マイク音声キャプチャ。専用シリアルキューで AVAudioEngine を操作。
public final class AudioCapture: @unchecked Sendable {
    private let engine = AVAudioEngine()
    private let queue = DispatchQueue(label: "com.kikitori.audio")
    private var tapInstalled = false
    
    public var targetFormat: AVAudioFormat?
    public var onAudioBuffer: ((AVAudioPCMBuffer) -> Void)?
    public var onAmplitude: (@MainActor @Sendable (Float) -> Void)?
    
    public init() {}
    
    public func start() async throws {
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            queue.async {
                do {
                    guard !self.tapInstalled else {
                        // 既に開始済み
                        cont.resume()
                        return
                    }
                    let input = self.engine.inputNode
                    let inputFmt = input.outputFormat(forBus: 0)
                    input.installTap(onBus: 0, bufferSize: 4096, format: inputFmt) { [weak self] buf, _ in
                        self?.deliver(buf, from: inputFmt)
                    }
                    self.tapInstalled = true
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
            guard self.tapInstalled else { return }
            self.tapInstalled = false
            engine.inputNode.removeTap(onBus: 0)
            engine.stop()
        }
    }
    
    private var _logFormatOnce = false
    
    /// バッファの RMS を計算（振幅 0.0〜1.0 に正規化）
    private static func _rms(from buffer: AVAudioPCMBuffer, format: AVAudioFormat) -> Float {
        let frames = Int(buffer.frameLength)
        guard frames > 0 else { return 0 }
        let ch = Int(buffer.format.channelCount)
        
        if let floatData = buffer.floatChannelData {
            var sum: Float = 0
            for c in 0..<ch {
                let ptr = floatData[c]
                for i in 0..<frames { sum += ptr[i] * ptr[i] }
            }
            return sqrt(sum / Float(frames * ch))
        } else if let int16Data = buffer.int16ChannelData {
            var sum: Float = 0
            let scale: Float = 32768
            for c in 0..<ch {
                let ptr = int16Data[c]
                for i in 0..<frames {
                    let v = Float(ptr[i]) / scale
                    sum += v * v
                }
            }
            return sqrt(sum / Float(frames * ch))
        }
        return 0
    }

    private func deliver(_ buffer: AVAudioPCMBuffer, from inputFmt: AVAudioFormat) {
        // 振幅コールバック（メインアクター）
        if let cb = onAmplitude {
            let rms = Self._rms(from: buffer, format: inputFmt)
            DispatchQueue.main.async { cb(rms) }
        }

        if let target = targetFormat {
            if !_logFormatOnce {
                _logFormatOnce = true
                DebugLogger.shared.log("AudioFormat: input=\(inputFmt) target=\(target) commonFormat=\(target.commonFormat.rawValue)")
            }
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
