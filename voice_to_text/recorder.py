"""録音ストリーム制御"""
from typing import Callable

import sounddevice as sd

from voice_to_text.audio_buffer import AudioBuffer


class Recorder:
    def __init__(
        self,
        audio_buffer: AudioBuffer,
        sample_rate: int = 16000,
        channels: int = 1,
        stream_factory=None,
    ):
        self._buffer = audio_buffer
        self._sample_rate = sample_rate
        self._channels = channels
        self._stream = None
        self._stream_factory = stream_factory or self._default_stream_factory

    def _default_stream_factory(self, *, callback):
        return sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="float32",
            callback=callback,
        )

    def start(self):
        self._buffer.start()
        self._stream = self._stream_factory(callback=self._on_audio)
        if self._stream is not None:
            self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        return self._buffer.stop()

    def _on_audio(self, indata, frames, time_info, status):
        if status:
            import sys

            print(f"[WARN] オーディオステータス: {status}", file=sys.stderr)
        if indata is not None and self._buffer.is_recording():
            self._buffer.append(indata.copy().reshape(-1))
