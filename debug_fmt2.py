#!/usr/bin/env python3
"""Test PCM buffer with int16 format."""
import sys, threading, time, numpy as np, wave
from Foundation import NSLocale, NSDate, NSRunLoop
from Speech import SFSpeechRecognizer, SFSpeechAudioBufferRecognitionRequest
from AVFoundation import AVAudioFormat, AVAudioPCMBuffer, AVAudioCommonFormat

auth_ev = threading.Event()
SFSpeechRecognizer.requestAuthorization_(lambda s: auth_ev.set() or None)
auth_ev.wait(timeout=5.0)

locale = NSLocale.alloc().initWithLocaleIdentifier_("ja-JP")
rec = SFSpeechRecognizer.alloc().initWithLocale_(locale)

with wave.open("/tmp/kikitori_debug_audio.wav", "r") as wf:
    data = wf.readframes(wf.getnframes())
    audio_i16 = np.frombuffer(data, dtype=np.int16)
    audio_f32 = audio_i16.astype(np.float32) / 32767.0

# Test 1: Standard format (float32)
fmt_f32 = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)
print(f"F32 fmt: sampleRate={fmt_f32.sampleRate()} ch={fmt_f32.channelCount()} common={fmt_f32.commonFormat()}", file=sys.stderr)

# Test 2: Explicit int16 interleaved
fmt_i16 = AVAudioFormat.alloc().initWithCommonFormat_sampleRate_channels_interleaved_(
    AVAudioCommonFormat(3), 16000.0, 1, True  # 3 = AVAudioPCMFormatInt16
)

# Test 3: Explicit float32 interleaved
fmt_f32_explicit = AVAudioFormat.alloc().initWithCommonFormat_sampleRate_channels_interleaved_(
    AVAudioCommonFormat(1), 16000.0, 1, True  # 1 = AVAudioPCMFormatFloat32
)

# Test 4: Explicit float32 planar
fmt_f32_planar = AVAudioFormat.alloc().initWithCommonFormat_sampleRate_channels_interleaved_(
    AVAudioCommonFormat(1), 16000.0, 1, False
)

for name, fmt, audio_data, dtype in [
    ("f32_std", fmt_f32, audio_f32, np.float32),
    ("f32_explicit_int", fmt_f32_explicit, audio_f32, np.float32),
    ("f32_planar", fmt_f32_planar, audio_f32, np.float32),
    ("i16_interleaved", fmt_i16, audio_i16, np.int16),
]:
    print(f"\n=== {name} ===", file=sys.stderr)
    if fmt is None:
        print(f"  fmt FAILED", file=sys.stderr)
        continue
    
    buf = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(fmt, len(audio_data))
    if buf is None:
        print(f"  buf FAILED", file=sys.stderr)
        continue
    buf.setFrameLength_(len(audio_data))
    
    # Fill buffer
    fd = buf.floatChannelData() if dtype == np.float32 else buf.int16ChannelData()
    cp = fd[0]
    nbytes = len(audio_data) * audio_data.dtype.itemsize
    npbuf = np.frombuffer(cp.as_buffer(len(audio_data)), dtype=audio_data.dtype).copy()
    npbuf[:] = audio_data[:len(npbuf)]
    
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
