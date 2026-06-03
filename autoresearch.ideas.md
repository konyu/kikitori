# Autoresearch Ideas — Kikitori Latency Optimization

## Done (21 experiments)
- [x] Streaming recognition on dedicated thread (transcribe 183ms → 0ms)
- [x] activate_app overlaps with recognition finalization
- [x] endAudio finalization wait 1s → 200ms
- [x] Thread join 2s → 500ms
- [x] Auto-stop properly uses streaming (stop+restart speech_analyzer)
- [x] Injector always clipboard paste (faster than per-char typing)
- [x] Clipboard save/restore after paste
- [x] Lazy import mlx_whisper (app startup 600ms → 127ms)
- [x] Benchmark variable naming fix
- [x] Async stop(): generation counter, no thread join. Saves ~700ms
- [x] Fire-and-forget activate_app_by_pid in daemon thread. Saves ~50-200ms
- [x] Remove dead _inject_direct code (always clipboard)
- [x] Code quality: ruff + mypy clean
- [x] Edge case: _on_auto_stop race with on_release safe (lock guard)
- [x] Clipboard protect non-text: skip restore when original empty (image/file)
- [x] Lazy import pynput.keyboard: _KEY_MAP, Controller, Key (app 127ms → 67ms)
- [x] Lazy import sounddevice + yaml (app 67ms → 38ms, 94% total reduction)
- [x] Stress test: 10 rapid-fire recording cycles (149 tests)
- [x] Fix clipboard corruption on rapid injections (generation counter for restore)
- [x] Remove dead type_threshold parameter
- [x] Additional edge case + reliability tests
- [x] Fix duplicate Corrections.load() call (was loaded twice: __init__ + App.load())
- [x] Make App.load() idempotent (_loaded flag, prevents double-load from PySide + run() path)
- [x] Remove all "Whisper"/"mlx" references from UI strings (settings_dialog.py)
- [x] Reduce endAudio finalization wait: 200→100ms daemon + 400→200ms hotpath

## Pipeline Summary
| Phase | Baseline | Current |
|-------|---------|---------|
| recorder.stop | ~5ms | ~0ms (async) |
| activate_app_by_pid | 50-200ms (blocking) | ~0ms (daemon thread) |
| speech_analyzer.stop | 200ms+500ms join | ~0ms (async, no join) |
| transcribe | 183ms (batch) | ~0ms (streaming, text available) |
| inject | 50-200ms (per-char) | ~1.8ms software + ~10-20ms OS |
| **Total** | **~711ms** | **~10-25ms (~97% improvement)** |

## App Import Time
| Phase | Time | Savings |
|-------|------|---------|
| Original | ~600ms | — |
| Lazy mlx_whisper | 127ms | -473ms |
| Lazy pynput.keyboard | 67ms | -60ms |
| Lazy sounddevice + yaml | ~38ms | -29ms |
| **Total** | **~38ms** | **~562ms (-94%)** |

## Backlog (all deferred — pipeline at theoretical minimum)
- Thread reuse: persistent speech_analyzer thread with condition variable. Small win (~10ms thread creation per cycle), complexity high. **Not worth it.**
- Overlap injection with final recognition: inject partial text immediately, update if final differs. Risky (double paste). **Not worth it.**
- Remove batch transcribe fallback: code simplification, but useful as user-configurable option. **Keep as fallback.**
- Eliminate double audio copy: <1ms per cycle. **Not worth complexity.**
- CGEventPost direct (bypass pynput): pynput already uses CGEventPost internally. **No benefit.**
- AXUIElement text injection: bypasses clipboard. Complex, fragile across apps. **Not worth it.**
- NSPasteboard direct (bypass pyperclip): pyperclip already thin wrapper. **~1ms savings, not worth dependency change.**
- Deduplicate activation threads: existing threads are daemon + harmless. **Not worth complexity.**
- GCD dispatch_after instead of threading.Timer: minor overhead savings. **Not worth jumping to PyObjC for timer.**
- Carbon SetFrontProcess for activation: deprecated API, risky. **Not worth it.**

## Remaining Latency Sources
- OS event queue processing: ~10-20ms (CGEventPost → dispatch → app handling)
- Clipboard IPC: ~1-2ms (NSPasteboard → pboard daemon)
- These are hardware/OS-level limits — not addressable in app code.

## Test Suite
- **149 tests** passing in ~0.55s
- Covers: hotkey management, injection, recorder, transcriber, edge cases
- Stress test: 10 rapid-fire cycles
- Rapid injection clipboard corruption test
- Empty clipboard protection test
