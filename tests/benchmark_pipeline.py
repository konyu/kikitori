"""End-to-end pipeline latency benchmark using fake components.

No hardware required. Measures wall-clock time from on_release to injection completion.
"""
import time
import threading
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kikitori.hotkey_manager import HotkeyManager
from pynput.keyboard import Key, KeyCode


class FakeSpeechAnalyzer:
    """Fake for SpeechAnalyzer that provides text immediately."""

    def __init__(self, text: str = "benchmark test text"):
        self._text = text
        self.on_partial_result = None
        self.on_final_result = None
        self._started = False
        self._stopped = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._stopped = True

    def get_latest_text(self) -> str:
        return self._text

    def append_audio(self, audio: np.ndarray) -> None:
        pass

    def is_final(self) -> bool:
        return True

    @property
    def started(self) -> bool:
        return self._started

    @property
    def stopped(self) -> bool:
        return self._stopped


class FakeRecorder:
    """Fake recorder that provides pre-recorded audio."""

    def __init__(self, audio: np.ndarray | None = None):
        self._audio = audio if audio is not None else np.zeros(8000, dtype=np.float32)  # 0.5s
        self.started = False
        self.stopped = False
        self._speech_analyzer = None

    def start(self) -> None:
        self.started = True

    def stop(self) -> np.ndarray:
        self.stopped = True
        return self._audio.copy()

    @property
    def speech_analyzer(self):
        return self._speech_analyzer

    @speech_analyzer.setter
    def speech_analyzer(self, value):
        self._speech_analyzer = value


class FakeInjector:
    """Fake injector that captures injected text."""

    def __init__(self):
        self.injected: list[str] = []

    def inject(self, text: str) -> None:
        if text:
            self.injected.append(text)


class FakeCorrections:
    """No-op corrections."""

    def correct(self, text: str) -> str:
        return text


DEFAULT_TEST_HOTKEY = ["ctrl", "alt"]
TEST_KWARGS = {
    "prompt": "",
    "language": "ja",
    "min_duration_ms": 0,
    "silence_rms_threshold": 0.0,
    "max_duration": 60,
    "corrections": FakeCorrections(),
    "on_state_change": None,
}


def run_benchmark(iterations: int = 100) -> dict:
    """Run the pipeline benchmark and return timing stats.

    Returns:
        dict with min_ms, max_ms, avg_ms, p50_ms, p95_ms, p99_ms
    """
    times = []

    audio = np.zeros(8000, dtype=np.float32)  # 0.5s audio
    speech_analyzer = FakeSpeechAnalyzer("benchmark output")

    for _ in range(iterations):
        rec = FakeRecorder(audio)
        rec.speech_analyzer = speech_analyzer
        inj = FakeInjector()
        mgr = HotkeyManager(
            rec, None, inj,  # transcriber not used (streaming)
            hotkey=DEFAULT_TEST_HOTKEY,
            speech_analyzer=speech_analyzer,
            **TEST_KWARGS,
        )

        # Simulate full cycle
        mgr.on_press(Key.ctrl_l)
        time.sleep(0.001)  # minimal time between press and release
        mgr.on_press(Key.alt)

        t0 = time.perf_counter()
        mgr.on_release(Key.alt)
        t1 = time.perf_counter()

        elapsed_ms = (t1 - t0) * 1000
        times.append(elapsed_ms)

    times.sort()
    n = len(times)

    return {
        "min_ms": float(np.min(times)),
        "max_ms": float(np.max(times)),
        "avg_ms": float(np.mean(times)),
        "p50_ms": float(np.median(times)),
        "p95_ms": float(times[int(n * 0.95)]),
        "p99_ms": float(times[int(n * 0.99)]),
    }


if __name__ == "__main__":
    import subprocess
    # Warmup
    for _ in range(3):
        run_benchmark(10)

    results = run_benchmark(100)
    print(f"METRIC pipeline_p50_ms={results['p50_ms']:.2f}")
    print(f"METRIC pipeline_p95_ms={results['p95_ms']:.2f}")
    print(f"METRIC pipeline_min_ms={results['min_ms']:.2f}")
    print(f"METRIC pipeline_max_ms={results['max_ms']:.2f}")
    print(f"METRIC pipeline_avg_ms={results['avg_ms']:.2f}")
    print(f"")
    print(f"Pipeline latency (on_release → injection complete):")
    print(f"  min: {results['min_ms']:.2f}ms")
    print(f"  avg: {results['avg_ms']:.2f}ms")
    print(f"  p50: {results['p50_ms']:.2f}ms")
    print(f"  p95: {results['p95_ms']:.2f}ms")
    print(f"  p99: {results['p99_ms']:.2f}ms")
    print(f"  max: {results['max_ms']:.2f}ms")
