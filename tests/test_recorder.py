"""Recorder のテスト — ストリーム制御と AudioBuffer 連携"""
import numpy as np
import pytest

from voice_to_text.audio_buffer import AudioBuffer
from voice_to_text.recorder import Recorder


class FakeStream:
    """テスト用: メモリ上でコールバックを駆動する偽ストリーム"""

    def __init__(self, callback, data_chunks=None):
        self.callback = callback
        self.data_chunks = data_chunks or []
        self._started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self._started = True
        for chunk in self.data_chunks:
            self.callback(chunk, None, None, None)

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


class TestRecorder:
    def test_start_creates_stream_and_starts_buffer(self):
        buf = AudioBuffer()
        created = {}

        def factory(*, callback):
            created["stream"] = FakeStream(callback)
            return created["stream"]

        rec = Recorder(buf, stream_factory=factory)
        rec.start()

        assert buf.is_recording()
        assert created["stream"]._started

    def test_stop_returns_recorded_audio(self):
        buf = AudioBuffer()
        chunks = [
            np.array([[0.1], [0.2]], dtype=np.float32),
            np.array([[0.3], [0.4]], dtype=np.float32),
        ]

        def factory(*, callback):
            return FakeStream(callback, data_chunks=chunks)

        rec = Recorder(buf, stream_factory=factory)
        rec.start()
        audio = rec.stop()

        np.testing.assert_array_equal(
            audio, np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        )
        assert not buf.is_recording()

    def test_stop_closes_stream(self):
        buf = AudioBuffer()
        stream = FakeStream(lambda *args: None)

        def factory(*, callback):
            return stream

        rec = Recorder(buf, stream_factory=factory)
        rec.start()
        rec.stop()

        assert stream.stopped
        assert stream.closed

    def test_stop_without_start_is_safe(self):
        buf = AudioBuffer()
        rec = Recorder(buf)
        # デフォルトの factory を使うと実際の sounddevice が動くので、
        # ここでは factory なしで start しない stop をテスト
        audio = rec.stop()
        assert audio.size == 0

    def test_stream_error_logged(self, capsys):
        """オーディオステータスエラーが標準エラーに出力される"""
        buf = AudioBuffer()

        def callback_with_error(indata, frames, time_info, status):
            # status 引数に文字列を渡してエラーシミュレート
            pass

        class ErrorStream(FakeStream):
            def start(self):
                self._started = True
                self.callback(None, 0, None, "Input overflow")

        rec = Recorder(buf, stream_factory=lambda *, callback: ErrorStream(callback))
        rec.start()
        rec.stop()

        captured = capsys.readouterr()
        assert "Input overflow" in captured.err
