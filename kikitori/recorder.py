"""録音ストリーム制御"""
import time
import sys
from typing import Callable

import sounddevice as sd

from kikitori.audio_buffer import AudioBuffer
from kikitori.config import AUDIO_DTYPE, CHANNELS, SAMPLE_RATE


class RecordError(Exception):
    """録音開始時のエラー"""


class Recorder:
    def __init__(
        self,
        audio_buffer: AudioBuffer,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
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
            dtype=AUDIO_DTYPE,
            callback=callback,
        )

    def start(self):
        """録音ストリームを開始する。

        スリープ復帰後などで PortAudio の内部状態が破損している場合、
        再初期化してリトライする。
        """
        self._buffer.start()
        try:
            self._stream = self._stream_factory(callback=self._on_audio)
            if self._stream is not None:
                self._stream.start()
        except sd.PortAudioError as e:
            print(
                f"[ERROR] 録音ストリーム開始エラー: {e} - PortAudio を再初期化してリトライします",
                file=sys.stderr,
            )
            self._buffer.stop()
            self._reinit_portaudio()
            # 再初期化後にリトライ
            try:
                self._buffer.start()
                self._stream = self._stream_factory(callback=self._on_audio)
                if self._stream is not None:
                    self._stream.start()
            except sd.PortAudioError as e2:
                self._buffer.stop()
                raise RecordError(
                    f"PortAudio 再初期化後も録音ストリームを開始できません: {e2}"
                ) from e2

    def _reinit_portaudio(self):
        """PortAudio を再初期化する。スリープ復帰後の破損状態から回復する。"""
        try:
            sd._terminate()
        except Exception:
            pass  # 終了に失敗しても続行
        time.sleep(0.1)
        sd._initialize()

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
        if indata is not None:
            # Copy the input data so we own the memory — sounddevice may reuse
            # indata after the callback returns.
            self._buffer.append(indata.copy().reshape(-1))
