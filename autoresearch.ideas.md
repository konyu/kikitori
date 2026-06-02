# Autoresearch Ideas — Kikitori Latency Optimization

## Done (12 experiments)
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

## Pipeline Summary
| Phase | Baseline | Current |
|-------|---------|---------|
| recorder.stop | ~5ms | ~0ms |
| activate_app_by_pid | 50-200ms (blocking) | ~0ms (daemon thread) |
| speech_analyzer.stop | 200ms+500ms | ~0ms (async, no join) |
| transcribe | 183ms (batch) | ~0ms (streaming) |
| inject | 50-200ms (per-char) | 20-50ms (clipboard Cmd+V) |
| **Total** | **~711ms** | **~20-50ms (~93% improvement)** |

## Backlog (deferred, diminished returns)
- Thread reuse: persistent speech_analyzer thread with condition variable. Small win (~10ms thread creation per cycle), complexity high.
- Overlap injection with final recognition: inject partial text immediately, update if final differs. Risky (double paste). Unnecessary with current latency.
- Remove batch transcribe fallback entirely if streaming reliable. Reduces code complexity, no latency impact.
- Profile PyObjC framework imports for startup improvement (saves ~30ms, not on hot path).
- Eliminate double audio copy: _on_audio copies indata, append_audio copies again. Saves ~128KB/s of allocation, <1ms per cycle.
