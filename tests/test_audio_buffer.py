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

    def test_start_resets_position_after_stop(self):
        """stop() の後 start() すると _pos がリセットされる"""
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

    def test_get_recent_amplitudes_empty_returns_zeros(self):
        buf = AudioBuffer()
        amps = buf.get_recent_amplitudes()
        assert amps.shape == (30,)
        assert np.all(amps == 0.0)

    def test_get_recent_amplitudes_with_audio(self):
        buf = AudioBuffer()
        buf.start()
        # Generate a sine wave with amplitude 0.5
        t = np.linspace(0, 0.1, int(0.1 * 16000), dtype=np.float32)
        audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
        buf.append(audio)
        amps = buf.get_recent_amplitudes()
        assert amps.shape == (30,)
        # At least some bars should be non-zero with a sine wave
        assert np.max(amps) > 0.0
        # Amplitudes should be clamped to [0, 1]
        assert np.all(amps >= 0.0)
        assert np.all(amps <= 1.0)
        buf.stop()

    def test_get_recent_amplitudes_respects_n_bars(self):
        buf = AudioBuffer()
        amps = buf.get_recent_amplitudes(n_bars=10)
        assert amps.shape == (10,)

    def test_append_dtype_conversion(self):
        """float64データがfloat32に変換される"""
        buf = AudioBuffer()
        buf.start()
        data = np.array([0.1, 0.2, 0.3], dtype=np.float64)
        buf.append(data)
        audio = buf.stop()
        assert audio.dtype == np.float32
        np.testing.assert_array_almost_equal(audio, np.array([0.1, 0.2, 0.3], dtype=np.float32))

    def test_buffer_overflow_truncates(self):
        """MAX_SAMPLESを超えるデータは切り捨てられる"""
        buf = AudioBuffer()
        max_samples = buf._MAX_SAMPLES
        buf.start()
        # Fill the buffer completely
        buf.append(np.ones(max_samples, dtype=np.float32))
        assert buf._pos == max_samples
        # Additional data should be ignored (position stays at max)
        buf.append(np.array([0.5, 0.5], dtype=np.float32))
        assert buf._pos == max_samples
        audio = buf.stop()
        assert len(audio) == max_samples

    def test_stop_returns_independent_copy(self):
        """stop()が返す配列はバッファのコピーであり、内部状態に影響しない"""
        buf = AudioBuffer()
        buf.start()
        buf.append(np.array([0.1, 0.2, 0.3], dtype=np.float32))
        audio = buf.stop()
        # Modify the returned array
        audio[0] = 999.0
        # Start new recording - buffer should be clean
        buf.start()
        buf.append(np.array([0.5], dtype=np.float32))
        new_audio = buf.stop()
        assert new_audio[0] == pytest.approx(0.5)
