#!/usr/bin/env python3
"""Test SFSpeechRecognizer with URL-based request (bypass PCM buffer)."""
import sys, threading, time
from Foundation import NSLocale, NSDate, NSRunLoop, NSURL
from Speech import SFSpeechRecognizer, SFSpeechURLRecognitionRequest

# auth
auth_ev = threading.Event()
SFSpeechRecognizer.requestAuthorization_(lambda s: auth_ev.set() or None)
auth_ev.wait(timeout=5.0)

# recognizer
for loc_str in ["ja-JP", "en-US"]:
    locale = NSLocale.alloc().initWithLocaleIdentifier_(loc_str)
    rec = SFSpeechRecognizer.alloc().initWithLocale_(locale)
    if rec is None:
        print(f"REC_FAIL {loc_str}", file=sys.stderr)
        continue
    print(f"REC_OK {loc_str} avail={rec.isAvailable()} ondev={rec.supportsOnDeviceRecognition()}", file=sys.stderr)
    
    # URL request
    url = NSURL.fileURLWithPath_("/tmp/kikitori_debug_audio.wav")
    for ondev in [True, False]:
        req = SFSpeechURLRecognitionRequest.alloc().initWithURL_(url)
        if req is None:
            print(f"  REQ_FAIL ondev={ondev}", file=sys.stderr)
            continue
        req.setRequiresOnDeviceRecognition_(ondev)
        
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
        deadline = time.perf_counter() + 5.0
        while time.perf_counter() < deadline and not done.is_set():
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                "kCFRunLoopDefaultMode",
                NSDate.dateWithTimeIntervalSinceNow_(0.1),
            )
        print(f"  URL_TEST {loc_str} ondev={ondev} text='{txt[0]}' err='{err[0]}'", file=sys.stderr)
