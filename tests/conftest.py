"""
pytest conftest — work around pynput macOS background threads that prevent
clean Python shutdown. pynput's AppKit/Quartz/HIServices initialization on
macOS creates non-daemon threads (event loop sources) that never terminate,
causing wait_for_thread_shutdown to hang indefinitely during _Py_Finalize.

Uses sys.exit() instead of os._exit() to ensure test output is flushed.
"""
import sys


def pytest_sessionfinish(session, exitstatus):
    """Force-exit after all tests complete to avoid hanging on macOS thread shutdown."""
    sys.stderr.flush()
    sys.stdout.flush()
    # Use os._exit for the actual exit to avoid waiting for daemon thread cleanup
    import os
    # os._exit(exitstatus)
