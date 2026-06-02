import time
import numpy as np
from kikitori.apple_speech import SpeechTranscriber

def main():
    transcriber = SpeechTranscriber()
    transcriber.load()

    # Generate 3 seconds of dummy audio (sine wave)
    sample_rate = 16000
    t = np.linspace(0, 3, 3 * sample_rate, False)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    # Warmup
    print("Warming up...")
    transcriber.transcribe(audio)

    print("Testing SFSpeechURLRecognitionRequest (current)...")
    start = time.time()
    res = transcriber.transcribe(audio)
    end = time.time()
    print(f"Result: {res}")
    print(f"Time: {end - start:.4f}s")

if __name__ == "__main__":
    main()