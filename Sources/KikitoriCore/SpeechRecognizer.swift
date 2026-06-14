import Foundation
@preconcurrency import AVFoundation
import Speech

/// バッチ型音声認識。SpeechAnalyzer + SpeechTranscriber 使用。
public final class SpeechRecognizer: @unchecked Sendable {
    private var transcriber: SpeechTranscriber?
    private var analyzer: SpeechAnalyzer?
    private var audioFormat: AVAudioFormat?
    private var isRunning = false
    
    private let lock = NSLock()
    private let audioStream: AsyncStream<AVAudioPCMBuffer>
    private var audioContinuation: AsyncStream<AVAudioPCMBuffer>.Continuation?
    private var setupTask: Task<Void, Never>?
    private var analyzerTask: Task<Void, Never>?
    private var _totalFrameCount: AVAudioFrameCount = 0
    private var buffersForRMS: [AVAudioPCMBuffer] = []
    
    /// 最低録音時間（ミリ秒）。これ未満は空文字を返す。
    public var minDurationMs: Int = 300

    /// 無音判定 RMS 閾値。0 で無効。
    public var silenceRmsThreshold: Double = 0.0001

    /// 認識言語コード（例: "ja", "en"）。デフォルト: "ja"
    public var language: String = "ja"

    /// 音声認識精度向上用の用語リスト（AnalysisContext.contextualStrings に渡す）
    /// ※現状はGlossary機能ドロップにより使用しませんが、APIとして残しています
    public var contextualStrings: [String] = []

    public var compatibleAudioFormat: AVAudioFormat? { audioFormat }
    public var totalFrameCount: AVAudioFrameCount { 
        lock.withLock { _totalFrameCount }
    }
    
    public init() {
        let (stream, continuation) = AsyncStream.makeStream(of: AVAudioPCMBuffer.self)
        self.audioStream = stream
        self.audioContinuation = continuation
        self.isRunning = true
    }
    
    public func start() {
        self.setupTask = Task {
            let locale = Self.locale(for: language)
            let t = SpeechTranscriber(locale: locale, preset: .transcription)
            let a = SpeechAnalyzer(modules: [t])
            
            let format = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [t])
            do {
                try await a.prepareToAnalyze(in: format)
            } catch {
                DebugLogger.shared.log("prepareToAnalyze failed: \(error)")
                return
            }

            if !contextualStrings.isEmpty {
                let ctx = AnalysisContext()
                ctx.contextualStrings[.general] = contextualStrings
                try? await a.setContext(ctx)
            }

            let shouldStartAnalyzer = lock.withLock { () -> Bool in
                self.transcriber = t
                self.analyzer = a
                self.audioFormat = format
                return self.isRunning
            }
            
            // isRunningがfalseなら、すでにstop()が呼ばれているので解析タスクを開始しつつ、すぐにストリームを終了させる
            // （audioContinuation?.finish() は stop() で呼ばれる）
            let converter = BufferConverter()
            let analyzerStream = SendableAnalyzerStream(base: audioStream.map { rawBuffer in
                if let f = format {
                    let converted = converter.convert(rawBuffer, to: f)
                    return AnalyzerInput(buffer: converted)
                }
                return AnalyzerInput(buffer: rawBuffer)
            })
            self.analyzerTask = Task {
                do {
                    _ = try await a.analyzeSequence(analyzerStream)
                } catch {
                    DebugLogger.shared.log("analyzeSequence error: \(error)")
                }
            }
        }
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
        lock.withLock {
            guard isRunning, let cont = audioContinuation else { return }
            cont.yield(buffer)
            _totalFrameCount += buffer.frameLength
            if silenceRmsThreshold > 0 {
                buffersForRMS.append(buffer)
            }
        }
    }
    
    public func stop() async -> String {
        // 初期化タスクが終わるのを確実に待つ（言語変更時などにprepareToAnalyzeが数秒かかる場合があるため）
        _ = await self.setupTask?.result

        let (t, a, format, frames, buffers) = lock.withLock {
            let t1 = self.transcriber
            let a1 = self.analyzer
            let f1 = self.audioFormat
            let fr = self._totalFrameCount
            let bufs = self.buffersForRMS
            self.audioContinuation?.finish()
            self.isRunning = false
            return (t1, a1, f1, fr, bufs)
        }

        DebugLogger.shared.log("stop() called, isRunning=false, totalFrames=\(frames), format=\(format?.description ?? "nil")")
        guard let t = t, let a = a else {
            return ""
        }

        // 最低録音時間フィルタ
        if minDurationMs > 0 {
            let sampleRate = format?.sampleRate ?? 16000
            let minFrames = AVAudioFrameCount(Double(minDurationMs) * sampleRate / 1000)
            if frames < minFrames {
                DebugLogger.shared.log("FILTER: too short, returning empty")
                return ""
            }
        }

        // 無音 RMS フィルタ
        if silenceRmsThreshold > 0 {
            let rms = calculateRMS(buffers)
            if rms < Float(silenceRmsThreshold) {
                DebugLogger.shared.log("FILTER: silence detected, returning empty")
                return ""
            }
        }

        try? await a.finalizeAndFinishThroughEndOfInput()
        _ = await self.analyzerTask?.result
        
        var text = ""
        do {
            for try await result in t.results {
                text += String(result.text.characters)
            }
        } catch { }
        let final = text.trimmingCharacters(in: .whitespacesAndNewlines)
        DebugLogger.shared.log("recognition result: '\(final)'")
        return final
    }

    private func calculateRMS(_ buffers: [AVAudioPCMBuffer]) -> Float {
        var sumSq: Float = 0
        var totalFrames: AVAudioFrameCount = 0
        for buf in buffers {
            let frames = Int(buf.frameLength)
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
        guard totalFrames > 0 else { return 0 }
        return sqrtf(sumSq / Float(totalFrames))
    }
}

// MARK: - Concurrency Workarounds

struct SendableAnalyzerStream: AsyncSequence, @unchecked Sendable {
    typealias Element = AnalyzerInput
    typealias AsyncIterator = Iterator
    
    let base: AsyncMapSequence<AsyncStream<AVAudioPCMBuffer>, AnalyzerInput>
    
    struct Iterator: AsyncIteratorProtocol {
        var base: AsyncMapSequence<AsyncStream<AVAudioPCMBuffer>, AnalyzerInput>.AsyncIterator
        mutating func next() async -> AnalyzerInput? {
            await base.next()
        }
    }
    
    func makeAsyncIterator() -> Iterator {
        Iterator(base: base.makeAsyncIterator())
    }
}

final class BufferConverter: @unchecked Sendable {
    private var converter: AVAudioConverter?
    private var outputFormat: AVAudioFormat?
    
    func convert(_ rawBuffer: AVAudioPCMBuffer, to format: AVAudioFormat) -> AVAudioPCMBuffer {
        if converter == nil || outputFormat != format {
            converter = AVAudioConverter(from: rawBuffer.format, to: format)
            outputFormat = format
        }
        guard let cvt = converter else { return rawBuffer }
        let outFrames = AVAudioFrameCount(Double(rawBuffer.frameLength) * format.sampleRate / rawBuffer.format.sampleRate)
        guard let out = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: outFrames) else { return rawBuffer }
        var err: NSError?
        cvt.convert(to: out, error: &err) { _, s in s.pointee = .haveData; return rawBuffer }
        return out.frameLength > 0 ? out : rawBuffer
    }
}
