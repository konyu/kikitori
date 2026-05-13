"""ホットキー状態管理（設定ファイルで変更可能）"""
import threading

from pynput.keyboard import Key, KeyCode

from kikitori.config import DEFAULT_HOTKEY, DEFAULT_LANGUAGE, MAX_DURATION, MIN_DURATION_MS, SAMPLE_RATE
from kikitori.injector import Injector
from kikitori.recorder import Recorder
from kikitori.transcriber import Transcriber


# キー名 → pynput Key/KeyCode 一覧（左右どちらでも反応）
_KEY_MAP: dict[str, list] = {
    "ctrl": [Key.ctrl_l, Key.ctrl_r],
    "control": [Key.ctrl_l, Key.ctrl_r],
    "alt": [Key.alt, Key.alt_r],
    "option": [Key.alt, Key.alt_r],
    "cmd": [Key.cmd, Key.cmd_r],
    "command": [Key.cmd, Key.cmd_r],
    "shift": [Key.shift, Key.shift_r],
}


def resolve_hotkey(names: list[str]) -> list[list]:
    """キー名のリストを、各名前に対応する Key オブジェクトのグループに変換する。"""
    groups = []
    for name in names:
        name = name.lower().strip()
        if name in _KEY_MAP:
            groups.append(_KEY_MAP[name])
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
    """キーをハッシュ可能な ID に変換（KeyCode の比較を安定化）。"""
    if isinstance(key, KeyCode):
        if key.vk is not None:
            return ("vk", key.vk)
        if key.char is not None:
            return ("char", key.char.lower())
    return key


class HotkeyManager:
    def __init__(
        self,
        recorder: Recorder,
        transcriber: Transcriber,
        injector: Injector,
        prompt: str = "",
        language: str = DEFAULT_LANGUAGE,
        max_duration: float = MAX_DURATION,
        min_duration_ms: float = MIN_DURATION_MS,
        hotkey: list[str] | None = None,
        timer_factory=None,
        on_state_change=None,
    ):
        self._recorder = recorder
        self._transcriber = transcriber
        self._injector = injector
        self._prompt = prompt
        self._language = language
        self._max_duration = max_duration
        self._min_duration_samples = int(min_duration_ms / 1000 * SAMPLE_RATE)
        self._timer_factory = timer_factory or threading.Timer
        self._timer = None
        self._is_recording = False
        self._lock = threading.Lock()
        self._on_state_change = on_state_change

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
        if self._should_transcribe(audio):
            text = self._transcriber.transcribe(
                audio, prompt=self._prompt, language=self._language
            )
            self._injector.inject(text)
        # キーがまだ押されていれば再録音、そうでなければタイマーをクリア
        with self._lock:
            if self._all_hotkey_pressed():
                self._is_recording = True
                if self._on_state_change:
                    self._on_state_change(True)
                self._recorder.start()
                self._start_auto_stop_timer()
            else:
                self._timer = None

    # ── 音声長判定 ────────────────────────────────────────────────────

    def _should_transcribe(self, audio) -> bool:
        """録音が最低長を満たしていればTrue。短すぎる場合はFalseを返しログ出力。"""
        if audio.size == 0:
            print("[INFO] 録音データが空です")
            return False
        if audio.size < self._min_duration_samples:
            duration_ms = audio.size / SAMPLE_RATE * 1000
            min_ms = self._min_duration_samples / SAMPLE_RATE * 1000
            print(f"[INFO] 録音が短すぎます（{duration_ms:.0f}ms < {min_ms:.0f}ms） — Whisperに渡しません")
            return False
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
        if self._is_hotkey_key(key):
            self._pressed_keys.add(_key_id(key))
        else:
            return

        with self._lock:
            if self._all_hotkey_pressed() and not self._is_recording:
                self._is_recording = True
                if self._on_state_change:
                    self._on_state_change(True)
                self._recorder.start()
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
            if self._should_transcribe(audio):
                text = self._transcriber.transcribe(
                    audio, prompt=self._prompt, language=self._language
                )
                self._injector.inject(text)

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
            if self._on_state_change:
                self._on_state_change(True)
        self._recorder.start()
        self._start_auto_stop_timer()

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
        if self._should_transcribe(audio):
            text = self._transcriber.transcribe(
                audio, prompt=self._prompt, language=self._language
            )
            self._injector.inject(text)
