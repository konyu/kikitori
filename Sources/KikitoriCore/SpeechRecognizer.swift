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
    
    /// 最低録音時間（ミリ秒）。これ未満は空文字を返す。
    public var minDurationMs: Int = 300

    /// 無音判定 RMS 閾値。0 で無効。
    public var silenceRmsThreshold: Double = 0.0001

    /// 認識言語コード（例: "ja", "en"）。デフォルト: "ja"
    public var language: String = "ja"

    public var compatibleAudioFormat: AVAudioFormat? { audioFormat }
    public var totalFrameCount: AVAudioFrameCount { bufferQueue.totalFrameCount }
    
    public init() {}
    
    public func start() async throws {
        let locale = Self.locale(for: language)
        let t = SpeechTranscriber(locale: locale, preset: .transcription)
        let a = SpeechAnalyzer(modules: [t])
        
        let format = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [t])
        try await a.prepareToAnalyze(in: format)
        
        self.transcriber = t
        self.analyzer = a
        self.audioFormat = format
        self.isRunning = true
    }
    
    /// 言語コード → Locale 変換
    private static func locale(for code: String) -> Locale {
        switch code {
        case "ja": return Locale(identifier: "ja-JP")
        case "en": return Locale(identifier: "en-US")
        case "zh": return Locale(identifier: "zh-CN")
        case "ko": return Locale(identifier: "ko-KR")
        case "fr": return Locale(identifier: "fr-FR")
        case "de": return Locale(identifier: "de-DE")
        default:  return Locale(identifier: "ja-JP")
        }
    }

    public func addAudio(_ buffer: AVAudioPCMBuffer) {
        guard isRunning else { return }
        bufferQueue.append(buffer)
    }
    
    public func stop() async -> String {
        DebugLogger.shared.log("stop() called, isRunning=\(isRunning), totalFrames=\(totalFrameCount), format=\(audioFormat?.description ?? "nil")")
        guard isRunning, let t = transcriber, let a = analyzer else {
            DebugLogger.shared.log("stop() early exit: isRunning=\(isRunning) transcriber=\(transcriber != nil) analyzer=\(analyzer != nil)")
            return ""
        }
        isRunning = false
        bufferQueue.finish()

        // 最低録音時間フィルタ
        if minDurationMs > 0 {
            let sampleRate = audioFormat?.sampleRate ?? 16000
            let minFrames = AVAudioFrameCount(Double(minDurationMs) * sampleRate / 1000)
            DebugLogger.shared.log("minDuration check: frames=\(totalFrameCount) minFrames=\(minFrames) minDurationMs=\(minDurationMs)")
            if totalFrameCount < minFrames {
                DebugLogger.shared.log("FILTER: too short, returning empty")
                return ""
            }
        }

        // 無音 RMS フィルタ
        if silenceRmsThreshold > 0 {
            let rms = bufferQueue.calculateRMS()
            DebugLogger.shared.log("silenceRms check: rms=\(rms) threshold=\(silenceRmsThreshold)")
            if rms < Float(silenceRmsThreshold) {
                DebugLogger.shared.log("FILTER: silence detected, returning empty")
                return ""
            }
        }

        DebugLogger.shared.log("starting recognizer pipeline...")
        let stream = bufferQueue.makeStream().map { AnalyzerInput(buffer: $0) }
        do { _ = try await a.analyzeSequence(stream) } catch { }
        try? await a.finalizeAndFinishThroughEndOfInput()
        
        var text = ""
        do {
            for try await result in t.results {
                text += String(result.text.characters)
            }
        } catch { }
        let final = text.trimmingCharacters(in: .whitespacesAndNewlines)
        DebugLogger.shared.log("recognition result: '\(final)' (len=\(final.count))")
        return final
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

    /// 全バッファの RMS（実効値）を計算する。無音判定用。
    func calculateRMS() -> Float {
        var sumSq: Float = 0
        var totalFrames: AVAudioFrameCount = 0
        lock.withLock {
            for buf in buffers {
                let frames = Int(buf.frameLength)
                // Float32 と Int16 の両対応
                if let floatData = buf.floatChannelData?.pointee {
                    for i in 0..<frames {
                        let s = floatData[i]
                        sumSq += s * s
                    }
                    totalFrames += buf.frameLength
                } else if let intData = buf.int16ChannelData?.pointee {
                    for i in 0..<frames {
                        let s = Float(intData[i]) / 32768.0
                        sumSq += s * s
                    }
                    totalFrames += buf.frameLength
                }
            }
        }
        guard totalFrames > 0 else { return 0 }
        return sqrtf(sumSq / Float(totalFrames))
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
