"""録音ストリーム制御"""
import sys
from typing import Callable

import sounddevice as sd

from kikitori.audio_buffer import AudioBuffer
from kikitori.config import AUDIO_DTYPE, BENCHMARK_MODE, CHANNELS, SAMPLE_RATE

class RecordError(Exception):
    """録音開始時のエラー"""

class Recorder:
    def __init__(
        self,
        audio_buffer: AudioBuffer,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        stream_factory=None,
        speech_analyzer: object | None = None,
    ):
        self._buffer = audio_buffer
        self._sample_rate = sample_rate
        self._channels = channels
        self._stream = None
        self._stream_factory = stream_factory or self._default_stream_factory
        self._speech_analyzer = speech_analyzer

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
        import time as _time
        t0 = _time.perf_counter()

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

        if BENCHMARK_MODE:
            elapsed = (_time.perf_counter() - t0) * 1000
            print(f"[BENCH] recorder_start: {elapsed:.1f}ms", flush=True)

    def _reinit_portaudio(self):
        """PortAudio を再初期化する。スリープ復帰後の破損状態から回復する。"""
        try:
            sd._terminate()
        except Exception:
            pass  # 終了に失敗しても続行
        sd._initialize()

    def stop(self):
        import time as _time
        t0 = _time.perf_counter()

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        result = self._buffer.stop()

        if BENCHMARK_MODE:
            elapsed = (_time.perf_counter() - t0) * 1000
            print(f"[BENCH] recorder_stop: {elapsed:.1f}ms", flush=True)

        return result

    def _on_audio(self, indata, frames, time_info, status):
        if status:
            import sys

            print(f"[WARN] オーディオステータス: {status}", file=sys.stderr)
        if indata is not None:
            # Copy the input data so we own the memory — sounddevice may reuse
            # indata after the callback returns.
            chunk = indata.copy().reshape(-1)
            self._buffer.append(chunk)
            if self._speech_analyzer is not None:
                self._speech_analyzer.append_audio(chunk)
