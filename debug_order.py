#!/usr/bin/env python3
"""Test PCM buffer: create task first, then append."""
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

for approach in ["before_task", "after_task"]:
    print(f"\n=== {approach} ===", file=sys.stderr)
    req = SFSpeechAudioBufferRecognitionRequest.alloc().init()
    req.setRequiresOnDeviceRecognition_(True)
    req.setAddsPunctuation_(True)
    
    all_texts = []
    done = threading.Event()
    errors = []
    
    def h(res, e):
        if e:
            errors.append(str(e))
            done.set()
        elif res:
            bt = res.bestTranscription()
            text = bt.formattedString() if bt else ""
            isf = res.isFinal()
            print(f"  HANDLER text='{text}' isFinal={isf}", file=sys.stderr)
            all_texts.append(text)
            if text or isf:
                done.set()
    
    if approach == "before_task":
        req.appendAudioPCMBuffer_(buf)
        req.endAudio()
    
    task = rec.recognitionTaskWithRequest_resultHandler_(req, h)
    
    if approach == "after_task":
        # Task already running, now append audio
        req.appendAudioPCMBuffer_(buf)
        req.endAudio()
    
    deadline = time.perf_counter() + 2.0
    while time.perf_counter() < deadline and not done.is_set():
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            "kCFRunLoopDefaultMode",
            NSDate.dateWithTimeIntervalSinceNow_(0.05),
        )
    
    print(f"  done={done.is_set()} texts={all_texts} errors={errors}", file=sys.stderr)
