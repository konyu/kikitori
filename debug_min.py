#!/usr/bin/env python3
"""Minimal SFSpeechRecognizer test."""
import sys, threading, time, numpy as np, wave

# load WAV
with wave.open("/tmp/kikitori_debug_audio.wav", "r") as wf:
    data = wf.readframes(wf.getnframes())
    audio = (np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0)

print("AUDIO_OK", len(audio), file=sys.stderr)

from Foundation import NSLocale, NSDate, NSRunLoop
from Speech import SFSpeechRecognizer, SFSpeechAudioBufferRecognitionRequest
from AVFoundation import AVAudioFormat, AVAudioPCMBuffer

# authorization
auth_event = threading.Event()
SFSpeechRecognizer.requestAuthorization_(lambda s: auth_event.set())
auth_event.wait(timeout=5.0)
print("AUTH_OK", file=sys.stderr)

# create recognizer
locale = NSLocale.alloc().initWithLocaleIdentifier_("ja-JP")
rec = SFSpeechRecognizer.alloc().initWithLocale_(locale)
print(f"REC_OK avail={rec.isAvailable()} ondev={rec.supportsOnDeviceRecognition()}", file=sys.stderr)

fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)

def test_audio(name, audio_data, rec):
    buf = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(fmt, len(audio_data))
    buf.setFrameLength_(len(audio_data))
    fd = buf.floatChannelData()
    cp = fd[0]
    npbuf = np.frombuffer(cp.as_buffer(len(audio_data)), dtype=np.float32).copy()
    npbuf[:] = audio_data[:len(npbuf)]
    
    for ondev in [True, False]:
        req = SFSpeechAudioBufferRecognitionRequest.alloc().init()
        req.setRequiresOnDeviceRecognition_(ondev)
        req.setAddsPunctuation_(True)
        req.appendAudioPCMBuffer_(buf)
        req.endAudio()
        
        done = threading.Event()
        txt = [""]
        err = [None]
        def h(res, e):
            if e: err[0] = str(e); done.set()
            elif res:
                bt = res.bestTranscription()
                if bt: txt[0] = bt.formattedString() or ""
                if txt[0] or res.isFinal(): done.set()
        
        task = rec.recognitionTaskWithRequest_resultHandler_(req, h)
        deadline = time.perf_counter() + 2.0
        while time.perf_counter() < deadline and not done.is_set():
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                "kCFRunLoopDefaultMode",
                NSDate.dateWithTimeIntervalSinceNow_(0.05),
            )
        print(f"TEST {name} ondev={ondev} wait={done.is_set()} text='{txt[0]}' err='{err[0]}'", file=sys.stderr)

# Test 1: WAV audio
print("\n--- WAV AUDIO ---", file=sys.stderr)
test_audio("wav", audio, rec)

# Test 2: Synthetic 440Hz sine wave
print("\n--- SYNTHETIC 440Hz ---", file=sys.stderr)
sr = 16000
t = np.arange(0, 2.0, 1/sr, dtype=np.float32)
synth = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
test_audio("sine440", synth, rec)

# Test 3: Test with different locales
for loc_name in ["en-US"]:
    locale2 = NSLocale.alloc().initWithLocaleIdentifier_(loc_name)
    rec2 = SFSpeechRecognizer.alloc().initWithLocale_(locale2)
    if rec2:
        print(f"\n--- LOCALE {loc_name} ---", file=sys.stderr)
        test_audio(f"wav-{loc_name}", audio, rec2)
