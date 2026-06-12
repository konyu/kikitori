"""Kikitori - Apple Silicon Mac向け音声認識入力ツール"""
import sys


class _StderrFilter:
    """IMKCFRunLoopWakeUpReliable のシステムログを抑制する stderr フィルタ。
    macOS Input Method Kit が出す無害な Mach ポート警告を握りつぶす。
    """

    def __init__(self, stderr):
        self._stderr = stderr

    def write(self, s: str) -> int:
        if "IMKCFRunLoopWakeUpReliable" not in s:
            return self._stderr.write(s)
        return 0

    def flush(self) -> None:
        self._stderr.flush()

    def __getattr__(self, name: str):
        return getattr(self._stderr, name)


if sys.stderr is not None:
    sys.stderr = _StderrFilter(sys.stderr)
