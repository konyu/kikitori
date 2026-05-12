"""スレッドセーフな録音バッファ管理"""
import threading

import numpy as np

from voice_to_text.config import AUDIO_DTYPE, MAX_DURATION, SAMPLE_RATE


class AudioBuffer:
    # Pre-allocate enough for max recording duration to avoid repeated allocations
    _MAX_SAMPLES = int(MAX_DURATION * SAMPLE_RATE)

    def __init__(self):
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

    def append(self, data: np.ndarray):
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

    def stop(self) -> np.ndarray:
        with self._lock:
            self._recording = False
            if self._pos == 0:
                return np.array([], dtype=AUDIO_DTYPE)
            return self._buf[:self._pos]
