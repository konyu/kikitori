"""ホットキー状態管理（設定ファイルで変更可能）"""
import threading

import numpy as np

# AppKit 初回インポートを前倒し（~46ms → ホットキー初回押下時の遅延を排除）
try:
    import AppKit  # noqa: F401
    from AppKit import NSWorkspace, NSRunningApplication  # noqa: F401
except ImportError:
    pass

from kikitori.config import (
    BENCHMARK_MODE,
    DEBUG,
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGE,
    MAX_DURATION,
    MIN_DURATION_MS,
    SAMPLE_RATE,
    SILENCE_RMS_THRESHOLD,
)
from kikitori.glossary import Glossary
from kikitori.injector import Injector
from kikitori.recorder import Recorder, RecordError
from kikitori.settings import get_frontmost_pid, activate_app_by_pid


# pynput.keyboard は遅延インポート（import に ~62ms かかるため）
_KEY_MAP_CACHE: dict[str, list] | None = None

def _build_key_map() -> dict[str, list]:
    """キー名 → pynput Key 一覧（左右どちらでも反応）。遅延構築。"""
    from pynput.keyboard import Key
    return {
        "ctrl": [Key.ctrl_l, Key.ctrl_r],
        "control": [Key.ctrl_l, Key.ctrl_r],
        "alt": [Key.alt, Key.alt_r],
        "option": [Key.alt, Key.alt_r],
        "cmd": [Key.cmd, Key.cmd_r],
        "command": [Key.cmd, Key.cmd_r],
        "shift": [Key.shift, Key.shift_r],
    }

def _get_key_map() -> dict[str, list]:
    global _KEY_MAP_CACHE
    if _KEY_MAP_CACHE is None:
        _KEY_MAP_CACHE = _build_key_map()
    return _KEY_MAP_CACHE


def resolve_hotkey(names: list[str]) -> list[list]:
    """キー名のリストを、各名前に対応する Key オブジェクトのグループに変換する。"""
    from pynput.keyboard import Key, KeyCode
    key_map = _get_key_map()
    groups = []
    for name in names:
        name = name.lower().strip()
        if name in key_map:
            groups.append(key_map[name])
        elif hasattr(Key, name):
            groups.append([getattr(Key, name)])
        elif len(name) == 1 and name.isalpha():
            # a-z などの1文字キー
            groups.append([KeyCode.from_char(name)])
        elif len(name) == 1 and name.isdigit():
            # 0-9 などの数字キー
            groups.append([KeyCode.from_char(name)])
        else:
            # 数値として解釈できれば仮想キーコードとみなす
            try:
                vk = int(name)
                groups.append([KeyCode.from_vk(vk)])
            except ValueError as exc:
                raise ValueError(f"未知のホットキー名です: {name}") from exc
    return groups


def _key_id(key):
    """キーをハッシュ可能な ID に変換（KeyCode の比較を安定化）。

    pynput の KeyCode は __eq__ が実装されていないため、vk/char で正規化する。
    """
    # hasattr で KeyCode を判定（遅延インポートのため isinstance を避ける）
    if hasattr(key, 'vk') and hasattr(key, 'char'):
        if key.vk is not None:
            return ("vk", key.vk)
        if key.char is not None:
            return ("char", key.char.lower())
    return key


class HotkeyManager:
    def __init__(
        self,
        recorder: Recorder,
        transcriber: object,
        injector: Injector,
        prompt: str = "",
        language: str = DEFAULT_LANGUAGE,
        max_duration: float = MAX_DURATION,
        min_duration_ms: float = MIN_DURATION_MS,
        hotkey: list[str] | None = None,
        timer_factory=None,
        on_state_change=None,
        glossary: "Glossary | None" = None,
        corrections = None,
        silence_rms_threshold: float = SILENCE_RMS_THRESHOLD,
        speech_analyzer: object | None = None,
    ):
        self._recorder = recorder
        self._transcriber = transcriber
        self._injector = injector
        self._prompt = prompt
        self._language = language
        self._max_duration = max_duration
        self._min_duration_samples = int(min_duration_ms / 1000 * SAMPLE_RATE)
        self._silence_rms_threshold = silence_rms_threshold
        self._timer_factory = timer_factory or threading.Timer
        self._timer = None
        self._is_recording = False
        self._target_pid = None  # 録音開始時のフォーカスPID
        self._lock = threading.Lock()
        self._on_state_change = on_state_change
        self._glossary: "Glossary | None" = glossary
        self._corrections = corrections
        self._speech_analyzer = speech_analyzer

        # ホットキー設定
        names = hotkey if hotkey is not None else DEFAULT_HOTKEY
        self._hotkey_groups = resolve_hotkey(names)
        # O(1) lookup sets
        self._hotkey_set: set = set()
        self._hotkey_group_sets: list[set] = []
        for group in self._hotkey_groups:
            key_ids = {_key_id(k) for k in group}
            self._hotkey_set.update(key_ids)
            self._hotkey_group_sets.append(key_ids)
        self._pressed_keys: set = set()

    # ── タイマー ────────────────────────────────────────────────────────

    def _start_auto_stop_timer(self):
        self._cancel_auto_stop_timer()
        self._timer = self._timer_factory(self._max_duration, self._on_auto_stop)
        self._timer.start()

    def _cancel_auto_stop_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_auto_stop(self):
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            if self._on_state_change:
                self._on_state_change(False)
        audio = self._recorder.stop()

        # ストリーミング認識を停止
        if self._speech_analyzer is not None:
            self._speech_analyzer.stop()

        if self._should_transcribe(audio):
            self._transcribe_and_inject(audio)
        # キーがまだ押されていれば再録音、そうでなければタイマーをクリア
        with self._lock:
            if self._all_hotkey_pressed():
                self._is_recording = True
                if self._on_state_change:
                    self._on_state_change(True)

                # ストリーミング認識を再開
                if self._speech_analyzer is not None:
                    self._speech_analyzer.on_partial_result = self._on_partial_speech
                    self._speech_analyzer.on_final_result = self._on_final_speech
                    self._speech_analyzer.start()

                self._recorder.start()
                self._start_auto_stop_timer()
            else:
                self._timer = None

    # ── 音声長判定 ────────────────────────────────────────────────────

    def _should_transcribe(self, audio) -> bool:
        """録音が最低長を満たし、無音でなければTrue。短すぎるか無音の場合はFalseを返しログ出力。"""
        import sys
        if DEBUG:
            print(f"[DEBUG] _should_transcribe: audio.size={audio.size} "
                  f"dtype={audio.dtype} ndim={audio.ndim}", flush=True)
        if audio.size == 0:
            print("[INFO] 録音データが空です")
            if DEBUG: print("[DEBUG] _should_transcribe → False (empty)", flush=True)
            return False
        if audio.size < self._min_duration_samples:
            duration_ms = audio.size / SAMPLE_RATE * 1000
            min_ms = self._min_duration_samples / SAMPLE_RATE * 1000
            print(f"[INFO] 録音が短すぎます（{duration_ms:.0f}ms < {min_ms:.0f}ms） — 音声認識に渡しません")
            return False
        rms = float(np.sqrt(np.dot(audio, audio) / audio.size))
        if DEBUG: print(f"[DEBUG] _should_transcribe: rms={rms:.6f} threshold={self._silence_rms_threshold}", flush=True)
        if rms < self._silence_rms_threshold:
            print(f"[INFO] 無音と判定されました（RMS={rms:.4f} < {self._silence_rms_threshold}） — 音声認識に渡しません")
            if DEBUG: print("[DEBUG] _should_transcribe → False (silence)", flush=True)
            return False
        if DEBUG: print("[DEBUG] _should_transcribe → True", flush=True)
        return True

    # ── キー判定 ────────────────────────────────────────────────────────

    def _is_hotkey_key(self, key) -> bool:
        """与えられたキーがホットキー設定に含まれるか。"""
        return _key_id(key) in self._hotkey_set

    def _all_hotkey_pressed(self) -> bool:
        """すべてのホットキーが押下されているか。"""
        for group_set in self._hotkey_group_sets:
            if group_set.isdisjoint(self._pressed_keys):
                return False
        return True

    # ── イベントハンドラ ───────────────────────────────────────────────

    def on_press(self, key):
        if not self._is_hotkey_key(key):
            return

        with self._lock:
            self._pressed_keys.add(_key_id(key))
            if self._all_hotkey_pressed() and not self._is_recording:
                self._is_recording = True
                # 録音開始時のフォーカスアプリを記憶
                self._target_pid = get_frontmost_pid()
                if self._on_state_change:
                    self._on_state_change(True)

                # ストリーミング認識を開始（録音と並行）
                if self._speech_analyzer is not None:
                    self._speech_analyzer.on_partial_result = self._on_partial_speech
                    self._speech_analyzer.on_final_result = self._on_final_speech
                    self._speech_analyzer.start()

                try:
                    self._recorder.start()
                except RecordError as e:
                    import sys
                    print(f"[ERROR] 録音開始失敗: {e}", file=sys.stderr)
                    if self._speech_analyzer is not None:
                        self._speech_analyzer.stop()
                    with self._lock:
                        self._is_recording = False
                        if self._on_state_change:
                            self._on_state_change(False)
                    return
                self._start_auto_stop_timer()

    def on_release(self, key):
        if not self._is_hotkey_key(key):
            return

        with self._lock:
            was_recording = self._is_recording
            self._pressed_keys.discard(_key_id(key))
            should_stop = was_recording and not self._all_hotkey_pressed()
            if should_stop:
                self._is_recording = False
                if self._on_state_change:
                    self._on_state_change(False)

        if should_stop:
            self._cancel_auto_stop_timer()
            audio = self._recorder.stop()

            # アプリ切替はバックグラウンドスレッドで（blocking AppKit 呼び出しを回避）
            target_pid = self._target_pid
            if target_pid is not None:
                threading.Thread(
                    target=lambda: activate_app_by_pid(target_pid),
                    daemon=True
                ).start()

            # ストリーミング認識を停止
            if self._speech_analyzer is not None:
                self._speech_analyzer.stop()

            self._transcribe_and_inject(audio)

    # ── 設定更新 ──────────────────────────────────────────────────────

    def update_hotkey(self, names: list[str]):
        """ホットキー設定を動的に更新（設定ファイル変更時）"""
        self._hotkey_groups = resolve_hotkey(names)
        self._hotkey_set = set()
        self._hotkey_group_sets = []
        for group in self._hotkey_groups:
            key_ids = {_key_id(k) for k in group}
            self._hotkey_set.update(key_ids)
            self._hotkey_group_sets.append(key_ids)

    # ── 公開 API ───────────────────────────────────────────────────────

    def is_recording(self) -> bool:
        with self._lock:
            return self._is_recording

    def start_recording(self):
        """メニューなど外部から録音を開始（ホットキー以外の入力手段用）"""
        with self._lock:
            if self._is_recording:
                return
            self._is_recording = True
            self._target_pid = get_frontmost_pid()
            if self._on_state_change:
                self._on_state_change(True)

        # ストリーミング認識を開始（transcribe を録音と並行実行するため）
        if self._speech_analyzer is not None:
            self._speech_analyzer.on_partial_result = self._on_partial_speech
            self._speech_analyzer.on_final_result = self._on_final_speech
            self._speech_analyzer.start()

        try:
            self._recorder.start()
        except RecordError as e:
            import sys
            print(f"[ERROR] 録音開始失敗: {e}", file=sys.stderr)
            if self._speech_analyzer is not None:
                self._speech_analyzer.stop()
            with self._lock:
                self._is_recording = False
                if self._on_state_change:
                    self._on_state_change(False)
            return
        self._start_auto_stop_timer()

    def _on_partial_speech(self, text: str) -> None:
        """ストリーミング認識の部分結果（コールバック用）。"""
        pass  # get_latest_text() で取得するため、ここでは何もしない

    def _on_final_speech(self, text: str) -> None:
        """ストリーミング認識の最終結果（コールバック用）。"""
        pass  # get_latest_text() で取得するため、ここでは何もしない

    def stop_recording(self):
        """メニューなど外部から録音を停止（ホットキー以外の入力手段用）"""
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            if self._on_state_change:
                self._on_state_change(False)
        self._cancel_auto_stop_timer()
        audio = self._recorder.stop()
        if DEBUG: print(f"[DEBUG] stop_recording: audio.size={audio.size} shape={audio.shape}", flush=True)

        # アプリ切替はバックグラウンドスレッドで
        target_pid = self._target_pid
        if target_pid is not None:
            threading.Thread(
                target=lambda: activate_app_by_pid(target_pid),
                daemon=True
            ).start()

        # ストリーミング認識を停止
        if self._speech_analyzer is not None:
            self._speech_analyzer.stop()

        self._transcribe_and_inject(audio)

    def _transcribe_and_inject(self, audio):
        """音声を認識・校正してペーストする。"""
        import time as _time
        t0 = _time.perf_counter()

        if not self._should_transcribe(audio):
            if DEBUG: print("[DEBUG] _transcribe_and_inject: SKIPPED (_should_transcribe=False)", flush=True)
            return

        # activate_app_by_pid は呼び出し元（stop_recording/on_release）で
        # speech_analyzer.stop() より先に実行済み。

        # ストリーミング認識の結果を取得
        text = ""
        if self._speech_analyzer is not None:
            # 最終認識結果が得られるまで待つ（speech_analyzer.stop() 後、
            # バックグラウンドの daemon スレッドが endAudio → 最終結果受信までに
            # 最大 ~200ms かかるため）
            self._speech_analyzer.wait_for_final(timeout=0.2)
            text = self._speech_analyzer.get_latest_text()
            if DEBUG: print(f"[DEBUG] _transcribe_and_inject: streaming_text='{text}' (len={len(text)})", flush=True)

        # ストリーミング結果がなければバッチ認識にフォールバック
        if not text:
            text = self._transcriber.transcribe(
                audio, prompt=self._get_effective_prompt(), language=self._language
            )
            if DEBUG: print(f"[DEBUG] _transcribe_and_inject: batch_text='{text}' (len={len(text)})", flush=True)

        if self._corrections is not None:
            text = self._corrections.correct(text)

        if DEBUG: print(f"[DEBUG] _transcribe_and_inject: final_text='{text}' (len={len(text)})", flush=True)

        t1 = _time.perf_counter()

        if DEBUG:
            if text:
                print(f"[DEBUG] _transcribe_and_inject: calling inject('{text}')", flush=True)
            else:
                print("[DEBUG] _transcribe_and_inject: text empty, inject will skip", flush=True)

        self._injector.inject(text)
        t2 = _time.perf_counter()

        if BENCHMARK_MODE:
            print(f"[BENCH] pipeline: transcribe={(t1-t0)*1000:.1f}ms "
                  f"inject={(t2-t1)*1000:.1f}ms "
                  f"total={(t2-t0)*1000:.1f}ms "
                  f"stream={'yes' if self._speech_analyzer is not None else 'no'}",
                  flush=True)

    # ── プロンプト生成 ───────────────────────────────────────────────

    def _get_effective_prompt(self) -> str:
        """glossary があれば用語追記したプロンプト、なければベースプロンプトを返す。"""
        if self._glossary is not None:
            terms = self._glossary.get_terms()
            if terms:
                prompt = self._glossary.build_prompt(self._prompt)
                if DEBUG: print(f"[DEBUG] プロンプトに専門用語を追記: {terms}", flush=True)
                return prompt
        return self._prompt
