#!/usr/bin/env python3
"""SFSpeechRecognizer 疎通確認スクリプト。

/tmp/kikitori_debug_audio.wav を読み込んで Apple Speech Framework で認識テスト。
"""
import sys
import wave
import numpy as np

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

# 2. モノラルに変換（必要なら）
if nch > 1:
    audio = audio.reshape(-1, nch).mean(axis=1)
    print(f"ステレオ→モノラル変換後: {len(audio)} frames")

# 3. 16kHz にリサンプル（必要なら）
if srate != 16000:
    from scipy.signal import resample
    new_len = int(len(audio) * 16000 / srate)
    audio = resample(audio, new_len).astype(np.float32)
    print(f"リサンプル {srate}→16000 Hz: {len(audio)} frames")

# 4. Apple Speech Framework で認識
from kikitori.apple_speech import SpeechTranscriber

print(f"\n--- SpeechTranscriber (on_device=True) ---")
st1 = SpeechTranscriber(locale="ja-JP", on_device=True, request_auth=True)
st1.load()
result1 = st1.transcribe(audio)
print(f"Result: '{result1}'")

print(f"\n--- SpeechTranscriber (on_device=False) ---")
st2 = SpeechTranscriber(locale="ja-JP", on_device=False, request_auth=False)
st2.load()
result2 = st2.transcribe(audio)
print(f"Result: '{result2}'")

if result1 or result2:
    print("\n*** 認識成功！問題は録音→認識パイプラインのどこかにある ***")
else:
    print("\n*** 認識失敗。WAVファイルの中身または macOS 音声認識設定を確認 ***")
