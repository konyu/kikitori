#!/usr/bin/env python3
"""Test explicit AVAudioPCMBuffer format."""
import sys, threading, time, numpy as np, wave
from Foundation import NSLocale, NSDate, NSRunLoop
from Speech import SFSpeechRecognizer, SFSpeechAudioBufferRecognitionRequest
from AVFoundation import AVAudioFormat, AVAudioPCMBuffer, AVAudioCommonFormat

# auth
auth_ev = threading.Event()
SFSpeechRecognizer.requestAuthorization_(lambda s: auth_ev.set() or None)
auth_ev.wait(timeout=5.0)
locale = NSLocale.alloc().initWithLocaleIdentifier_("ja-JP")
rec = SFSpeechRecognizer.alloc().initWithLocale_(locale)

# load WAV
with wave.open("/tmp/kikitori_debug_audio.wav", "r") as wf:
    data = wf.readframes(wf.getnframes())
    audio = (np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0)

for approach in ["standard", "explicit_planar", "explicit_interleaved"]:
    print(f"\n=== {approach} ===", file=sys.stderr)
    
    if approach == "standard":
        fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)
    elif approach == "explicit_planar":
        fmt = AVAudioFormat.alloc().initWithCommonFormat_sampleRate_channels_interleaved_(
            AVAudioCommonFormat.FormatFloat32, 16000.0, 1, False
        )
    else:  # explicit_interleaved
        fmt = AVAudioFormat.alloc().initWithCommonFormat_sampleRate_channels_interleaved_(
            AVAudioCommonFormat.FormatFloat32, 16000.0, 1, True
        )
    
    if fmt is None:
        print(f"  fmt creation failed", file=sys.stderr)
        continue
    
    buf = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(fmt, len(audio))
    if buf is None:
        print(f"  buf creation failed", file=sys.stderr)
        continue
    buf.setFrameLength_(len(audio))
    
    fd = buf.floatChannelData()
    cp = fd[0]
    npbuf = np.frombuffer(cp.as_buffer(len(audio)), dtype=np.float32).copy()
    npbuf[:] = audio[:len(npbuf)]
    
    for ondev in [True, False]:
        req = SFSpeechAudioBufferRecognitionRequest.alloc().init()
        req.setRequiresOnDeviceRecognition_(ondev)
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
        
        rec.recognitionTaskWithRequest_resultHandler_(req, h)
        deadline = time.perf_counter() + 2.0
        while time.perf_counter() < deadline and not done.is_set():
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                "kCFRunLoopDefaultMode",
                NSDate.dateWithTimeIntervalSinceNow_(0.05),
            )
        print(f"  ondev={ondev} text='{txt[0]}' err='{err[0]}'", file=sys.stderr)
