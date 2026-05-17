"""Recorder のテスト — ストリーム制御と AudioBuffer 連携"""
import numpy as np
import pytest

from kikitori.audio_buffer import AudioBuffer
from kikitori.recorder import Recorder


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

        class ErrorStream(FakeStream):
            def start(self):
                self._started = True
                self.callback(None, 0, None, "Input overflow")

        rec = Recorder(buf, stream_factory=lambda *, callback: ErrorStream(callback))
        rec.start()
        rec.stop()

        captured = capsys.readouterr()
        assert "Input overflow" in captured.err

    def test_on_audio_appends_data_to_buffer(self):
        """_on_audio が indata を reshape してバッファに追加する"""
        buf = AudioBuffer()
        rec = Recorder(buf, stream_factory=lambda *, callback: FakeStream(callback))

        # 直接 _on_audio を呼び出し
        indata = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
        buf.start()
        rec._on_audio(indata, 3, None, None)
        audio = buf.stop()

        np.testing.assert_array_equal(audio, np.array([0.1, 0.2, 0.3], dtype=np.float32))

    def test_on_audio_handles_none_indata(self):
        """indata が None でもクラッシュしない"""
        buf = AudioBuffer()
        rec = Recorder(buf, stream_factory=lambda *, callback: FakeStream(callback))

        buf.start()
        # indata=None でも例外が発生しないこと
        rec._on_audio(None, 0, None, None)
        audio = buf.stop()
        assert audio.size == 0

    def test_on_audio_no_status_does_not_print(self, capsys):
        """status が None の場合は何も出力しない"""
        buf = AudioBuffer()
        rec = Recorder(buf, stream_factory=lambda *, callback: FakeStream(callback))

        buf.start()
        indata = np.array([[0.1]], dtype=np.float32)
        rec._on_audio(indata, 1, None, None)
        buf.stop()

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_on_audio_creates_independent_copy(self):
        """_on_audio が indata のコピーを作成する（元の配列変更に影響されない）"""
        buf = AudioBuffer()
        rec = Recorder(buf, stream_factory=lambda *, callback: FakeStream(callback))

        indata = np.array([[0.1], [0.2]], dtype=np.float32)
        buf.start()
        rec._on_audio(indata, 2, None, None)
        # 元の indata を変更
        indata[0, 0] = 999.0
        audio = buf.stop()

        # コピーされているので変更の影響を受けない
        np.testing.assert_array_equal(audio, np.array([0.1, 0.2], dtype=np.float32))

    def test_multiple_stream_chunks_accumulate(self):
        """複数回のストリームチャンクが正しく蓄積される"""
        buf = AudioBuffer()
        chunks = [
            np.array([[0.1]], dtype=np.float32),
            np.array([[0.2], [0.3]], dtype=np.float32),
            np.array([[0.4]], dtype=np.float32),
        ]

        def factory(*, callback):
            return FakeStream(callback, data_chunks=chunks)

        rec = Recorder(buf, stream_factory=factory)
        rec.start()
        audio = rec.stop()

        np.testing.assert_array_equal(audio, np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32))
