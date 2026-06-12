"""スレッドセーフな録音バッファ管理"""
import threading

from kikitori.config import AUDIO_DTYPE, MAX_DURATION, SAMPLE_RATE

# 遅延 numpy import（初回の AudioBuffer インスタンス化時に C 拡張をロード）
_np = None

def _get_np():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np

class AudioBuffer:
    # Pre-allocate enough for max recording duration to avoid repeated allocations
    _MAX_SAMPLES = int(MAX_DURATION * SAMPLE_RATE)

    def __init__(self):
        np = _get_np()
        self._recording = False
        self._pos = 0
        self._buf = np.zeros(self._MAX_SAMPLES, dtype=AUDIO_DTYPE)
        self._lock = threading.Lock()

    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def start(self):
        with self._lock:
            self._recording = True
            self._pos = 0

    def append(self, data):
        np = _get_np()
        with self._lock:
            if not self._recording:
                return
            n = len(data)
            end = self._pos + n
            if end > self._MAX_SAMPLES:
                n = self._MAX_SAMPLES - self._pos
                end = self._MAX_SAMPLES
            if n > 0:
                if data.dtype == AUDIO_DTYPE:
                    self._buf[self._pos:end] = data[:n]
                else:
                    self._buf[self._pos:end] = data[:n].astype(AUDIO_DTYPE)
                self._pos = end

    def stop(self):
        np = _get_np()
        with self._lock:
            self._recording = False
            if self._pos == 0:
                return np.array([], dtype=AUDIO_DTYPE)
            # Return a copy, not a view — the pre-allocated buffer may be reused
            # (e.g. _on_auto_stop restarts recording) while the caller is still
            # reading the returned audio.
            return self._buf[:self._pos].copy()

    def get_rms(self) -> float:
        """録音データの RMS（実効値）を返す。無音判定用。"""
        np = _get_np()
        with self._lock:
            if self._pos == 0:
                return 0.0
            chunk = self._buf[:self._pos]
            return float(np.sqrt(np.dot(chunk, chunk) / chunk.size))

    def get_recent_amplitudes(self, n_bars: int = 30, window_ms: float = 50.0):
        """直近の音声振幅を n_bars 個分取得する。UI 波形表示用。"""
        np = _get_np()
        with self._lock:
            if self._pos == 0:
                return np.zeros(n_bars, dtype=AUDIO_DTYPE)
            samples_per_bar = max(1, int(window_ms / 1000 * SAMPLE_RATE))
            amplitudes = np.zeros(n_bars, dtype=AUDIO_DTYPE)
            for i in range(n_bars):
                end = self._pos - i * samples_per_bar
                start = max(0, end - samples_per_bar)
                if end <= 0:
                    break
                chunk = self._buf[start:end]
                if len(chunk) > 0:
                    amplitudes[n_bars - 1 - i] = min(np.max(np.abs(chunk)) * 4.0, 1.0)
            return amplitudes
