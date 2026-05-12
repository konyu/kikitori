"""スレッドセーフな録音バッファ管理"""
import threading
from typing import List

import numpy as np

from voice_to_text.config import AUDIO_DTYPE


class AudioBuffer:
    def __init__(self):
        self._recording = False
        self._buffer: List[np.ndarray] = []
        self._lock = threading.Lock()

    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def start(self):
        with self._lock:
            self._recording = True
            self._buffer = []

    def append(self, data: np.ndarray):
        with self._lock:
            if self._recording:
                self._buffer.append(data.astype(AUDIO_DTYPE).copy())

    def stop(self) -> np.ndarray:
        with self._lock:
            self._recording = False
            if not self._buffer:
                return np.array([], dtype=AUDIO_DTYPE)
            audio = np.concatenate(self._buffer, axis=0)
            self._buffer = []
            return audio
