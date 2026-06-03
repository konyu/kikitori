#!/usr/bin/env python3
"""Verify PCM buffer fix."""
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

# FIX: no .copy() — write directly into PCM buffer view
pbuf = cp.as_buffer(len(audio))
npbuf = np.frombuffer(pbuf, dtype=np.float32)  # NO .copy()!
print(f"npbuf writable: {npbuf.flags.writeable}", file=sys.stderr)

# Verify writing into the view updates the PCM buffer
# Fill with zeros first, then write audio
npbuf.fill(0.0)
# Check PCM buffer is zeroed
req_check = SFSpeechAudioBufferRecognitionRequest.alloc().init()
# Now write audio
npbuf[:] = audio[:len(npbuf)]
print(f"After write: npbuf[0:5]={npbuf[:5]} audio[0:5]={audio[:5]}", file=sys.stderr)

# Test recognition
req = SFSpeechAudioBufferRecognitionRequest.alloc().init()
req.setRequiresOnDeviceRecognition_(True)
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
        print(f"HANDLER text='{text}' isFinal={isf}", file=sys.stderr)
        all_texts.append(text)
        if text or isf:
            done.set()

rec.recognitionTaskWithRequest_resultHandler_(req, h)
deadline = time.perf_counter() + 2.0
while time.perf_counter() < deadline and not done.is_set():
    NSRunLoop.currentRunLoop().runMode_beforeDate_(
        "kCFRunLoopDefaultMode",
        NSDate.dateWithTimeIntervalSinceNow_(0.05),
    )

print(f"\nFINAL: texts={all_texts}", file=sys.stderr)
