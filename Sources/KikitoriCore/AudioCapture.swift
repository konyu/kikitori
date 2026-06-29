@preconcurrency import AVFoundation

/// マイク音声キャプチャ。専用シリアルキューで AVAudioEngine を操作。
public final class AudioCapture: @unchecked Sendable {
    private let engine = AVAudioEngine()
    private let queue = DispatchQueue(label: "com.kikitori.audio")
    private var tapInstalled = false
    private var firstBufferDelivered = false
    
    public var targetFormat: AVAudioFormat? {
        didSet {
            if targetFormat != oldValue { _converter = nil }
        }
    }
    public var onAudioBuffer: ((AVAudioPCMBuffer) -> Void)?
    public var onAmplitude: (@MainActor @Sendable (Float) -> Void)?
    
    private var _converter: AVAudioConverter?
    
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
                    input.installTap(onBus: 0, bufferSize: 512, format: inputFmt) { [weak self] buf, _ in
                        self?.deliver(buf, from: inputFmt)
                    }
                    self.tapInstalled = true
                    self.firstBufferDelivered = false
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
    
    /// バッファの RMS を計算（振幅 0.0〜1.0 に正規化）
    private static func _rms(from buffer: AVAudioPCMBuffer) -> Float {
        let frames = Int(buffer.frameLength)
        guard frames > 0, let ptr = buffer.floatChannelData?[0] else { return 0 }
        var sum: Float = 0
        for i in 0..<frames { sum += ptr[i] * ptr[i] }
        return sqrt(sum / Float(frames))
    }

    private func deliver(_ buffer: AVAudioPCMBuffer, from inputFmt: AVAudioFormat) {
        let isFirst = !firstBufferDelivered
        if isFirst && onAudioBuffer != nil {
            firstBufferDelivered = true
            DebugLogger.log("AudioCapture: FIRST buffer delivered, frames=\(buffer.frameLength), rate=\(buffer.format.sampleRate)")
        }
        
        // 初回バッファの振幅はスキップ（ハードウェア起動時の過渡ノイズを除去）
        if !isFirst, let cb = onAmplitude {
            let rms = Self._rms(from: buffer)
            DispatchQueue.main.async { cb(rms) }
        }

        if let target = targetFormat {
            // フォーマットが同一なら変換スキップ
            if inputFmt == target {
                onAudioBuffer?(buffer)
                return
            }
            if _converter == nil {
                _converter = AVAudioConverter(from: inputFmt, to: target)
            }
            guard let cvt = _converter else { return }
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
