import Testing
import KikitoriCore

@Test func speechRecognizerInit() {
    let r = SpeechRecognizer()
    #expect(r.compatibleAudioFormat == nil)
    #expect(r.totalFrameCount == 0)
}

@Test func totalFrameCount() {
    let r = SpeechRecognizer()
    #expect(r.totalFrameCount == 0)
}
