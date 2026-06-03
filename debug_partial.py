#!/usr/bin/env python3
"""Test PCM buffer with shouldReportPartialResults."""
import sys, threading, time, numpy as np, wave
from Foundation import NSLocale, NSDate, NSRunLoop
from Speech import SFSpeechRecognizer, SFSpeechAudioBufferRecognitionRequest
from AVFoundation import AVAudioFormat, AVAudioPCMBuffer

auth_ev = threading.Event()
SFSpeechRecognizer.requestAuthorization_(lambda s: auth_ev.set() or None)
auth_ev.wait(timeout=5.0)

locale = NSLocale.alloc().initWithLocaleIdentifier_("ja-JP")
rec = SFSpeechRecognizer.alloc().initWithLocale_(locale)

with wave.open("/tmp/kikitori_debug_audio.wav", "r") as wf:
    data = wf.readframes(wf.getnframes())
    audio = (np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0)

fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)
buf = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(fmt, len(audio))
buf.setFrameLength_(len(audio))
fd = buf.floatChannelData()
cp = fd[0]
npbuf = np.frombuffer(cp.as_buffer(len(audio)), dtype=np.float32).copy()
npbuf[:] = audio[:len(npbuf)]

# Test with shouldReportPartialResults
req = SFSpeechAudioBufferRecognitionRequest.alloc().init()
req.setRequiresOnDeviceRecognition_(True)
req.setShouldReportPartialResults_(True)
req.setAddsPunctuation_(True)
req.appendAudioPCMBuffer_(buf)
req.endAudio()

all_texts = []
done = threading.Event()

def h(res, e):
    if e:
        print(f"HANDLER ERROR: {e}", file=sys.stderr)
        done.set()
    elif res:
        bt = res.bestTranscription()
        text = bt.formattedString() if bt else ""
        isf = res.isFinal()
        alts = res.transcriptions()
        print(f"HANDLER text='{text}' isFinal={isf} alt_count={len(alts) if alts else 0}", file=sys.stderr)
        for i, alt in enumerate(alts if alts else []):
            print(f"  alt[{i}]: '{alt.formattedString()}'", file=sys.stderr)
        all_texts.append((text, isf))
        if isf or text:
            done.set()

rec.recognitionTaskWithRequest_resultHandler_(req, h)
deadline = time.perf_counter() + 2.0
while time.perf_counter() < deadline and not done.is_set():
    NSRunLoop.currentRunLoop().runMode_beforeDate_(
        "kCFRunLoopDefaultMode",
        NSDate.dateWithTimeIntervalSinceNow_(0.05),
    )

print(f"\nFINAL: texts={all_texts}", file=sys.stderr)
