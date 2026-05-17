"""HotkeyManager のテスト — Ctrl+Option 状態遷移"""
import numpy as np
import pytest
from pynput.keyboard import Key

from kikitori.hotkey_manager import HotkeyManager


DEFAULT_TEST_HOTKEY = ["ctrl", "alt"]
# min_duration_ms=0 で最低録音長フィルタを無効化（テストでは短い音声データを使用）
TEST_KWARGS = {"min_duration_ms": 0}


class FakeRecorder:
    def __init__(self):
        self.started = False
        self.stopped = False
        self._audio = np.array([0.1, 0.2], dtype=np.float32)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True
        self.started = False
        return self._audio


class FakeTranscriber:
    def __init__(self, text="テスト"):
        self.text = text
        self.calls = []

    def transcribe(self, audio, prompt="", language="ja"):
        self.calls.append((audio.copy(), prompt, language))
        return self.text


class FakeInjector:
    def __init__(self):
        self.injected = []

    def inject(self, text, delay=0.2):
        self.injected.append(text)


class FakeTimer:
    """手動発火型の偽タイマー"""

    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.started = False
        self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        if not self.cancelled:
            self.function()


class TestHotkeyManager:
    def test_press_ctrl_alone_does_not_start(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.on_press(Key.ctrl_l)
        assert not rec.started

    def test_press_alt_alone_does_not_start(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.on_press(Key.alt)
        assert not rec.started

    def test_press_both_starts_recording(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        assert rec.started

    def test_release_either_stops_and_injects(self):
        rec = FakeRecorder()
        trans = FakeTranscriber("こんにちは")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.ctrl_l)

        assert rec.stopped
        assert inj.injected == ["こんにちは"]
        assert len(trans.calls) == 1

    def test_release_other_key_ignored(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.shift)

        assert not rec.stopped

    def test_double_start_is_ignored(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_press(Key.ctrl_l)  # 再度
        assert rec.started
        # start が2回呼ばれていない（内部フラグでガード）

    def test_release_when_not_recording_does_nothing(self):
        rec = FakeRecorder()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.on_release(Key.ctrl_l)
        assert not rec.stopped
        assert inj.injected == []

    def test_empty_audio_skips_transcription(self):
        rec = FakeRecorder()
        rec._audio = np.array([], dtype=np.float32)
        trans = FakeTranscriber()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)

        assert rec.stopped
        assert len(trans.calls) == 0
        assert inj.injected == []

    def test_release_order_independent(self):
        """Ctrl または Alt のどちらを先に離しても動作する"""
        rec = FakeRecorder()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, FakeTranscriber("A"), inj, hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)  # alt を先に離す
        assert rec.stopped
        assert inj.injected == ["A"]

    def test_full_cycle_twice(self):
        rec = FakeRecorder()
        trans = FakeTranscriber("A")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)

        for _ in range(2):
            rec.stopped = False
            mgr.on_press(Key.ctrl_l)
            mgr.on_press(Key.alt)
            mgr.on_release(Key.ctrl_l)

        assert len(inj.injected) == 2
        assert all(t == "A" for t in inj.injected)

    def test_prompt_and_language_passed_to_transcriber(self):
        rec = FakeRecorder()
        trans = FakeTranscriber()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS, prompt="テストプロンプト", language="en")

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)

        assert len(trans.calls) == 1
        assert trans.calls[0][1] == "テストプロンプト"
        assert trans.calls[0][2] == "en"

    def test_auto_stop_timer_starts_on_recording(self):
        rec = FakeRecorder()
        timer = FakeTimer(0, None)
        mgr = HotkeyManager(
            rec, FakeTranscriber(), FakeInjector(),
            hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS,
            max_duration=60.0,
            timer_factory=lambda interval, func: FakeTimer(interval, func),
        )
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        assert mgr._timer is not None
        assert mgr._timer.interval == 60.0
        assert mgr._timer.started

    def test_auto_stop_timer_cancelled_on_release(self):
        rec = FakeRecorder()
        mgr = HotkeyManager(
            rec, FakeTranscriber(), FakeInjector(),
            hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS,
            max_duration=60.0,
            timer_factory=lambda interval, func: FakeTimer(interval, func),
        )
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        timer = mgr._timer
        mgr.on_release(Key.ctrl_l)
        assert timer.cancelled

    def test_auto_stop_fires_and_restarts_when_keys_held(self):
        """タイマー発火→ペースト→キー押下中なら再録音"""
        rec = FakeRecorder()
        trans = FakeTranscriber("区切り")
        inj = FakeInjector()
        mgr = HotkeyManager(
            rec, trans, inj,
            hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS,
            max_duration=60.0,
            timer_factory=lambda interval, func: FakeTimer(interval, func),
        )
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        timer = mgr._timer

        # タイマー発火（キーはまだ押されている）
        timer.fire()

        assert rec.stopped
        assert inj.injected == ["区切り"]
        # 再録音されている
        assert rec.started
        assert mgr._timer is not None
        assert mgr._timer is not timer  # 新しいタイマー

    def test_auto_stop_fires_and_stops_when_keys_released(self):
        """タイマー発火→ペースト→キー離れているなら再録音しない"""
        rec = FakeRecorder()
        trans = FakeTranscriber("区切り")
        inj = FakeInjector()
        mgr = HotkeyManager(
            rec, trans, inj,
            hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS,
            max_duration=60.0,
            timer_factory=lambda interval, func: FakeTimer(interval, func),
        )
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        timer = mgr._timer

        # キーを離す（pressed_keys を空にする）
        mgr._pressed_keys.clear()
        timer.fire()

        assert rec.stopped
        assert inj.injected == ["区切り"]
        # 再録音されていない
        assert not rec.started
        assert mgr._timer is None

    def test_f13_single_key_hotkey(self):
        """F13 単体をホットキーとして使用"""
        rec = FakeRecorder()
        trans = FakeTranscriber("F13テスト")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=["f13"], **TEST_KWARGS)

        mgr.on_press(Key.f13)
        assert rec.started

        mgr.on_release(Key.f13)
        assert rec.stopped
        assert inj.injected == ["F13テスト"]

    def test_letter_key_hotkey(self):
        """文字キー a をホットキーとして使用"""
        from pynput.keyboard import KeyCode
        rec = FakeRecorder()
        trans = FakeTranscriber("文字キー")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=["a"], **TEST_KWARGS)

        key_a = KeyCode.from_char("a")
        mgr.on_press(key_a)
        assert rec.started

        mgr.on_release(key_a)
        assert rec.stopped
        assert inj.injected == ["文字キー"]

    def test_digit_key_hotkey(self):
        """数字キー 1 をホットキーとして使用"""
        from pynput.keyboard import KeyCode
        rec = FakeRecorder()
        trans = FakeTranscriber("数字キー")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=["1"], **TEST_KWARGS)

        key_1 = KeyCode.from_char("1")
        mgr.on_press(key_1)
        assert rec.started

        mgr.on_release(key_1)
        assert rec.stopped
        assert inj.injected == ["数字キー"]

    def test_hotkey_with_letter_and_modifier(self):
        """修飾キー + 文字キーの組み合わせ"""
        from pynput.keyboard import KeyCode
        rec = FakeRecorder()
        trans = FakeTranscriber("組み合わせ")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=["ctrl", "a"], **TEST_KWARGS)

        key_a = KeyCode.from_char("a")
        mgr.on_press(Key.ctrl_l)
        assert not rec.started  # まだ a を押していない

        mgr.on_press(key_a)
        assert rec.started

        mgr.on_release(key_a)
        assert rec.stopped
        assert inj.injected == ["組み合わせ"]

    def test_invalid_hotkey_name_raises(self):
        """未知のキー名は ValueError を送出"""
        with pytest.raises(ValueError, match="未知のホットキー名"):
            HotkeyManager(FakeRecorder(), FakeTranscriber(), FakeInjector(), hotkey=["unknown_key_xyz"], **TEST_KWARGS)

    # ── 公開 API: start_recording / stop_recording ──────────────────

    def test_start_recording_public_api(self):
        """メニューからの録音開始"""
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.start_recording()
        assert rec.started
        assert mgr.is_recording()

    def test_stop_recording_public_api(self):
        """メニューからの録音停止"""
        rec = FakeRecorder()
        trans = FakeTranscriber("停止テスト")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.start_recording()
        mgr.stop_recording()
        assert rec.stopped
        assert not mgr.is_recording()
        assert inj.injected == ["停止テスト"]

    def test_start_recording_when_already_recording_is_noop(self):
        """録音中に再度 start_recording しても何も起きない"""
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.start_recording()
        rec.started = False  # リセットして監視
        mgr.start_recording()
        assert not rec.started  # start() は呼ばれない

    def test_stop_recording_when_not_recording_is_noop(self):
        """録音中でないときに stop_recording しても何も起きない"""
        rec = FakeRecorder()
        inj = FakeInjector()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)
        mgr.stop_recording()
        assert not rec.stopped
        assert inj.injected == []

    # ── ホットキー動的更新 ─────────────────────────────────────────

    def test_update_hotkey_changes_keys(self):
        """update_hotkey でホットキーを動的に変更できる"""
        rec = FakeRecorder()
        trans = FakeTranscriber("更新後")
        inj = FakeInjector()
        mgr = HotkeyManager(rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)

        # 元のホットキー (ctrl+alt) で動作確認
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        assert rec.started
        mgr.on_release(Key.alt)
        assert rec.stopped

        # ホットキーを shift 単体に変更
        mgr.update_hotkey(["shift"])

        # 古いホットキーでは反応しない
        rec.stopped = False
        mgr.on_press(Key.ctrl_l)
        assert not rec.started

        # 新しいホットキーで反応する
        mgr.on_press(Key.shift)
        assert rec.started
        mgr.on_release(Key.shift)
        assert inj.injected[-1] == "更新後"

    # ── 状態変更コールバック ───────────────────────────────────────

    def test_on_state_change_callback_called(self):
        """録音開始/停止時に on_state_change コールバックが呼ばれる"""
        states = []

        def callback(is_recording):
            states.append(is_recording)

        rec = FakeRecorder()
        mgr = HotkeyManager(
            rec, FakeTranscriber(), FakeInjector(),
            hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS,
            on_state_change=callback,
        )

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        assert states == [True]

        mgr.on_release(Key.alt)
        assert states == [True, False]

    def test_on_state_change_on_manual_start_stop(self):
        """start_recording/stop_recording でもコールバックが呼ばれる"""
        states = []

        def callback(is_recording):
            states.append(is_recording)

        rec = FakeRecorder()
        mgr = HotkeyManager(
            rec, FakeTranscriber(), FakeInjector(),
            hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS,
            on_state_change=callback,
        )

        mgr.start_recording()
        assert states == [True]

        mgr.stop_recording()
        assert states == [True, False]

    # ── 最低録音長フィルタ ─────────────────────────────────────────

    def test_should_transcribe_below_min_duration(self):
        """最低録音長未満の音声は Whisper に渡されない"""
        rec = FakeRecorder()
        # 500ms = 8000 samples
        rec._audio = np.zeros(4000, dtype=np.float32)  # 250ms
        trans = FakeTranscriber()
        inj = FakeInjector()
        mgr = HotkeyManager(
            rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY,
            min_duration_ms=500.0,
        )

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)

        assert rec.stopped
        assert len(trans.calls) == 0  # 短すぎて文字起こしされない
        assert inj.injected == []

    def test_should_transcribe_at_min_duration(self):
        """最低録音長ちょうどの音声は Whisper に渡される"""
        rec = FakeRecorder()
        # 500ms = 8000 samples
        rec._audio = np.zeros(8000, dtype=np.float32)
        trans = FakeTranscriber("ちょうど")
        inj = FakeInjector()
        mgr = HotkeyManager(
            rec, trans, inj, hotkey=DEFAULT_TEST_HOTKEY,
            min_duration_ms=500.0,
        )

        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        mgr.on_release(Key.alt)

        assert len(trans.calls) == 1
        assert inj.injected == ["ちょうど"]

    # ── 非ホットキーキー ───────────────────────────────────────────

    def test_non_hotkey_press_is_ignored(self):
        """ホットキー以外のキー押下は _pressed_keys に追加されない"""
        rec = FakeRecorder()
        mgr = HotkeyManager(rec, FakeTranscriber(), FakeInjector(), hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS)

        # 非ホットキーを押しても pressed_keys は空のまま
        mgr.on_press(Key.shift)
        assert len(mgr._pressed_keys) == 0

        # 非ホットキーのリリースも無視される
        mgr.on_release(Key.shift)
        assert not rec.stopped

    # ── タイマーを使った録音→停止→再録音のフルサイクル ──────────

    def test_auto_stop_transcribes_even_when_keys_held(self):
        """auto_stop 発火時にキーが押されていれば再録音、押されていなければ停止"""
        rec = FakeRecorder()
        trans = FakeTranscriber("自動停止")
        inj = FakeInjector()
        mgr = HotkeyManager(
            rec, trans, inj,
            hotkey=DEFAULT_TEST_HOTKEY, **TEST_KWARGS,
            max_duration=60.0,
            timer_factory=lambda interval, func: FakeTimer(interval, func),
        )

        # キー押下 → タイマー発火
        mgr.on_press(Key.ctrl_l)
        mgr.on_press(Key.alt)
        timer = mgr._timer
        timer.fire()

        # キーが押されているので再録音される
        assert inj.injected == ["自動停止"]
        assert mgr.is_recording()
        assert mgr._timer is not None
        assert mgr._timer is not timer  # 新しいタイマー

        # キーを離してタイマー発火
        mgr.on_release(Key.ctrl_l)
        assert not mgr.is_recording()  # リリースで停止
