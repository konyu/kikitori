import Testing
import KikitoriCore

@Test func speechRecognizerInit() {
    let r = SpeechRecognizer()
    #expect(r.compatibleAudioFormat == nil)
    #expect(r.totalFrameCount == 0)
    #expect(r.minDurationMs == 300)
}

@Test func totalFrameCount() {
    let r = SpeechRecognizer()
    #expect(r.totalFrameCount == 0)
}

@Test func minDurationMsDefault() {
    let r = SpeechRecognizer()
    #expect(r.minDurationMs == 300)
}

@Test func minDurationMsCustom() {
    let r = SpeechRecognizer()
    r.minDurationMs = 500
    #expect(r.minDurationMs == 500)
}

@Test func minDurationMsZeroDisabled() {
    let r = SpeechRecognizer()
    r.minDurationMs = 0
    #expect(r.minDurationMs == 0)
}

@Test func silenceRmsThresholdDefault() {
    let r = SpeechRecognizer()
    #expect(r.silenceRmsThreshold == 0.0001)
}

@Test func silenceRmsThresholdCustom() {
    let r = SpeechRecognizer()
    r.silenceRmsThreshold = 0.01
    #expect(r.silenceRmsThreshold == 0.01)
}

@Test func silenceRmsThresholdZeroDisabled() {
    let r = SpeechRecognizer()
    r.silenceRmsThreshold = 0
    #expect(r.silenceRmsThreshold == 0)
}
