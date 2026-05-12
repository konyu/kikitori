"""AudioBuffer のテスト — スレッドセーフな録音バッファ管理"""
import numpy as np
import pytest

from kikitori.audio_buffer import AudioBuffer


class TestAudioBuffer:
    def test_init_not_recording(self):
        buf = AudioBuffer()
        assert not buf.is_recording()

    def test_start_recording_sets_flag_and_clears_buffer(self):
        buf = AudioBuffer()
        buf.append(np.array([0.1, 0.2]))
        buf.start()
        assert buf.is_recording()
        assert buf.stop().size == 0

    def test_append_only_while_recording(self):
        buf = AudioBuffer()
        buf.start()
        buf.append(np.array([0.1, 0.2]))
        buf.append(np.array([0.3, 0.4]))
        audio = buf.stop()
        np.testing.assert_array_equal(audio, np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32))

    def test_append_ignored_when_not_recording(self):
        buf = AudioBuffer()
        buf.append(np.array([0.1, 0.2]))
        assert not buf.is_recording()
        assert buf.stop().size == 0

    def test_stop_returns_empty_when_no_data(self):
        buf = AudioBuffer()
        buf.start()
        audio = buf.stop()
        assert audio.size == 0
        assert not buf.is_recording()

    def test_stop_clears_internal_state(self):
        buf = AudioBuffer()
        buf.start()
        buf.append(np.array([0.1]))
        buf.stop()
        buf.start()
        assert buf.stop().size == 0

    def test_multiple_start_stop_cycles(self):
        buf = AudioBuffer()
        for i in range(3):
            buf.start()
            buf.append(np.array([float(i)], dtype=np.float32))
            audio = buf.stop()
            assert audio.size == 1
            assert audio[0] == pytest.approx(float(i))
