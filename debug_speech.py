#!/usr/bin/env python3
"""SFSpeechRecognizer 疎通確認スクリプト。

/tmp/kikitori_debug_audio.wav を読み込んで Apple Speech Framework で認識テスト。
"""
import sys
import threading
import wave
import numpy as np

from Foundation import NSLocale, NSError
from Speech import (
    SFSpeechRecognizer,
    SFSpeechRecognizerAuthorizationStatus,
    SFSpeechAudioBufferRecognitionRequest,
    SFSpeechRecognitionResult,
)
from AVFAudio import AVAudioFormat, AVAudioPCMBuffer

WAV_PATH = "/tmp/kikitori_debug_audio.wav"

# 1. WAV ファイル読み込み
try:
    with wave.open(WAV_PATH, "r") as wf:
        nch = wf.getnchannels()
        srate = wf.getframerate()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)
        audio_int16 = np.frombuffer(data, dtype=np.int16)
        audio = audio_int16.astype(np.float32) / 32767.0
    print(f"WAV: {nframes} frames, {srate} Hz, {nch} ch, RMS={float(np.sqrt(np.dot(audio,audio)/len(audio))):.6f}")
except FileNotFoundError:
    print(f"WAVファイルが見つかりません: {WAV_PATH}")
    print("先に BENCHMARK_MODE=true python main.py を実行して録音してください。")
    sys.exit(1)

# 2. 認可状態チェック
auth_status = SFSpeechRecognizer.authorizationStatus()
status_names = {0: "notDetermined", 1: "denied", 2: "restricted", 3: "authorized"}
print(f"認可状態: {status_names.get(auth_status, auth_status)}")

if auth_status != 3:  # not authorized
    print("音声認識が認可されていません。システム設定で許可してください。")
    # 認可リクエスト
    auth_event = threading.Event()
    auth_result = [None]
    def _handler(s):
        auth_result[0] = s
        auth_event.set()
    SFSpeechRecognizer.requestAuthorization_(_handler)
    auth_event.wait(timeout=5.0)
    print(f"認可リクエスト結果: {status_names.get(auth_result[0], auth_result[0])}")

# 3. ロケール確認
for loc_str in ["ja-JP", "en-US", "zh-CN", "ko-KR"]:
    locale = NSLocale.alloc().initWithLocaleIdentifier_(loc_str)
    rec = SFSpeechRecognizer.alloc().initWithLocale_(locale)
    if rec is not None:
        on_dev = rec.supportsOnDeviceRecognition()
        avail = rec.isAvailable()
        print(f"  locale={loc_str}: available={avail}, supportsOnDevice={on_dev}")
    else:
        print(f"  locale={loc_str}: recognizer creation FAILED")

# 4. 認識テスト
locale = NSLocale.alloc().initWithLocaleIdentifier_("ja-JP")
recognizer = SFSpeechRecognizer.alloc().initWithLocale_(locale)
if recognizer is None:
    print("ja-JP recognizer 作成失敗")
    sys.exit(1)

print(f"\nrecognizer.isAvailable = {recognizer.isAvailable()}")
print(f"recognizer.supportsOnDeviceRecognition = {recognizer.supportsOnDeviceRecognition()}")

# PCMバッファ作成
fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)
buffer = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(fmt, len(audio))
buffer.setFrameLength_(len(audio))

float_data = buffer.floatChannelData()
print(f"  floatChannelData type: {type(float_data)}")
print(f"  floatChannelData: {float_data}")

if float_data is None:
    print("floatChannelData() returned None")
    sys.exit(1)

# floatChannelData が PyObjCPointer の場合、as_buffer() を直接使う
try:
    channel_ptr = float_data[0]
except (TypeError, IndexError):
    # PyObjCPointer はインデックス不可の可能性がある
    # その場合は float_data 自体が最初のチャンネルポインタ
    print("  float_data[0] failed, trying direct as_buffer")
    channel_ptr = float_data

buf = channel_ptr.as_buffer(len(audio))
np_buf = np.frombuffer(buf, dtype=np.float32).copy()
np_buf[:] = audio[:len(np_buf)]

for on_dev in [True, False]:
    print(f"\n--- on_device = {on_dev} ---")
    request = SFSpeechAudioBufferRecognitionRequest.alloc().init()
    request.setRequiresOnDeviceRecognition_(on_dev)
    request.setAddsPunctuation_(True)
    request.appendAudioPCMBuffer_(buffer)
    request.endAudio()

    import time
    done = threading.Event()
    texts = [""]
    errors = []

    def handler(result, error):
        if error:
            errors.append(str(error))
            done.set()
        elif result:
            best = result.bestTranscription()
            if best:
                texts[0] = best.formattedString() or ""
            if texts[0] or result.isFinal():
                done.set()

    task = recognizer.recognitionTaskWithRequest_resultHandler_(request, handler)
    print(f"  task created: {task is not None}")

    wait_result = done.wait(timeout=2.0)
    print(f"  done_event: {wait_result}")
    print(f"  text: '{texts[0]}'")
    print(f"  errors: {errors}")

