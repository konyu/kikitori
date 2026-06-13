import Foundation
@preconcurrency import AVFoundation
import Speech

/// バッチ型音声認識。SpeechAnalyzer + SpeechTranscriber 使用。
public final class SpeechRecognizer: @unchecked Sendable {
    private let bufferQueue = BufferQueue()
    private var transcriber: SpeechTranscriber?
    private var analyzer: SpeechAnalyzer?
    private var audioFormat: AVAudioFormat?
    private var isRunning = false
    
    public var compatibleAudioFormat: AVAudioFormat? { audioFormat }
    public var totalFrameCount: AVAudioFrameCount { bufferQueue.totalFrameCount }
    
    public init() {}
    
    public func start() async throws {
        let locale = Locale(identifier: "ja-JP")
        let t = SpeechTranscriber(locale: locale, preset: .transcription)
        let a = SpeechAnalyzer(modules: [t])
        
        let format = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [t])
        try await a.prepareToAnalyze(in: format)
        
        self.transcriber = t
        self.analyzer = a
        self.audioFormat = format
        self.isRunning = true
    }
    
    public func addAudio(_ buffer: AVAudioPCMBuffer) {
        guard isRunning else { return }
        bufferQueue.append(buffer)
    }
    
    public func stop() async -> String {
        guard isRunning, let t = transcriber, let a = analyzer else { return "" }
        isRunning = false
        bufferQueue.finish()
        
        let stream = bufferQueue.makeStream().map { AnalyzerInput(buffer: $0) }
        do { _ = try await a.analyzeSequence(stream) } catch { }
        try? await a.finalizeAndFinishThroughEndOfInput()
        
        var text = ""
        do {
            for try await result in t.results {
                text += String(result.text.characters)
            }
        } catch { }
        return text.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

// MARK: - BufferQueue

final class BufferQueue: @unchecked Sendable {
    private let lock = NSLock()
    private var buffers: [AVAudioPCMBuffer] = []
    private var finished = false
    private var _totalFrameCount: AVAudioFrameCount = 0
    
    var totalFrameCount: AVAudioFrameCount {
        lock.withLock { _totalFrameCount }
    }
    
    func append(_ buffer: AVAudioPCMBuffer) {
        lock.withLock {
            guard !finished else { return }
            buffers.append(buffer)
            _totalFrameCount += buffer.frameLength
        }
    }
    
    func finish() {
        lock.withLock { finished = true }
    }
    
    func makeStream() -> AsyncStream<AVAudioPCMBuffer> {
        AsyncStream { continuation in
            lock.withLock {
                for buf in buffers { continuation.yield(buf) }
            }
            let done: Bool = lock.withLock { finished }
            if done {
                continuation.finish()
            } else {
                Task.detached { [weak self] in
                    while true {
                        try? await Task.sleep(nanoseconds: 50_000_000)
                        guard let self else { break }
                        let d: Bool = self.lock.withLock { self.finished && self.buffers.isEmpty }
                        if d { break }
                    }
                    continuation.finish()
                }
            }
        }
    }
}
