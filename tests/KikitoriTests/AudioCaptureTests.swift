import Testing
import KikitoriCore
@preconcurrency import AVFoundation

@Test func audioCaptureInit() {
    let c = AudioCapture()
    #expect(c.targetFormat == nil)
    #expect(c.onAudioBuffer == nil)
}
