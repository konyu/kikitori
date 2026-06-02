# Autoresearch Ideas — Kikitori Latency Optimization

## Done
- [x] Streaming recognition on dedicated thread (transcribe ~0ms)
- [x] activate_app overlaps with recognition finalization
- [x] endAudio finalization wait 1s → 200ms
- [x] Thread join 2s → 500ms
- [x] Auto-stop properly uses streaming (stop+restart speech_analyzer)
- [x] Injector always clipboard paste (faster than per-char typing)
- [x] Clipboard save/restore after paste
- [x] Lazy import mlx_whisper (app startup 600ms → 127ms)

## Backlog (deferred, promising but not urgent)
- async stop(): don't join speech_analyzer thread, let daemon thread clean up. Saves ~200ms from user-perceived latency. Need generation counter for safe restart.
- Thread reuse: persistent speech_analyzer thread with condition variable instead of creating new thread per recording session
- Pre-activate app during recording (anticipatory app switch) — might feel jarring to user
- Overlap injection with final recognition: inject partial text immediately, update if final differs (risky — double paste)
- Remove batch transcribe fallback entirely if streaming is reliable — simplifies pipeline
- Profile PyObjC framework imports for further startup improvement (AVFoundation, Speech, AppKit ~30ms each)
