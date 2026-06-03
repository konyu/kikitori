#!/usr/bin/env python3
"""Full URL recognition test with partial results."""
import sys, threading, time
from Foundation import NSLocale, NSDate, NSRunLoop, NSURL
from Speech import SFSpeechRecognizer, SFSpeechURLRecognitionRequest

auth_ev = threading.Event()
SFSpeechRecognizer.requestAuthorization_(lambda s: auth_ev.set() or None)
auth_ev.wait(timeout=5.0)

locale = NSLocale.alloc().initWithLocaleIdentifier_("ja-JP")
rec = SFSpeechRecognizer.alloc().initWithLocale_(locale)

url = NSURL.fileURLWithPath_("/tmp/kikitori_debug_audio.wav")
req = SFSpeechURLRecognitionRequest.alloc().initWithURL_(url)
req.setRequiresOnDeviceRecognition_(True)
req.setAddsPunctuation_(True)
# req.shouldReportPartialResults = True  # get incremental results

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
        all_texts.append((text, isf))
        if isf:
            done.set()
rec.recognitionTaskWithRequest_resultHandler_(req, h)

# Wait with run loop
deadline = time.perf_counter() + 5.0
while time.perf_counter() < deadline and not done.is_set():
    NSRunLoop.currentRunLoop().runMode_beforeDate_(
        "kCFRunLoopDefaultMode",
        NSDate.dateWithTimeIntervalSinceNow_(0.1),
    )

print(f"\nFINAL: all texts = {all_texts}", file=sys.stderr)
