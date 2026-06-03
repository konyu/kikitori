"""App の統合テスト"""
from pynput.keyboard import Key

from kikitori.app import App
from kikitori.audio_buffer import AudioBuffer
from kikitori.hotkey_manager import HotkeyManager
from kikitori.injector import Injector
from kikitori.recorder import Recorder


class FakeListener:
    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release
        self.joined = False
        self.started = False
        self.stopped = False
        self._thread = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def is_alive(self):
        return self.started and not self.stopped

    def join(self):
        self.joined = True

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class FakeTranscriberForApp:
    def __init__(self):
        self.loaded = False

    def load(self):
        self.loaded = True

    def transcribe(self, audio, prompt="", language="ja"):
        return "認識結果"


class TestApp:
    def test_app_initializes_components(self):
        app = App()
        assert app._sample_rate == 16000
        assert app._buffer is not None
        assert app._recorder is not None
        assert app._transcriber is not None
        assert app._injector is not None
        assert app._hotkey is not None

    def test_app_loads_model(self):
        trans = FakeTranscriberForApp()
        app = App()
        app._transcriber = trans
        app.load()
        assert trans.loaded

    def test_app_runs_listener(self):
        listener = FakeListener()
        app = App()
        app.run(listener_factory=lambda **kwargs: listener)
        assert listener.joined

    def test_app_run_background_starts_listener(self):
        """run_background がリスナーをバックグラウンドで開始する"""
        listener = FakeListener()
        app = App()

        def factory(**kwargs):
            return listener

        app.run_background(listener_factory=factory)
        assert listener.started

        # クリーンアップ
        app.stop_background()

    def test_app_stop_background_stops_listener(self):
        """stop_background がリスナーを停止する"""
        listener = FakeListener()
        app = App()

        app.run_background(listener_factory=lambda **kwargs: listener)
        assert listener.started

        app.stop_background()
        assert listener.stopped
        assert app._listener is None

    def test_app_accepts_config_params(self):
        """すべての設定パラメータが App に受け入れられる"""
        app = App(
            sample_rate=44100,
            channels=2,
            prompt="カスタムプロンプト",
            language="en",
            max_duration=30.0,
            min_duration_ms=1000.0,
            hotkey=["shift"],
        )
        assert app._sample_rate == 44100
        assert app._channels == 2
        assert app._prompt == "カスタムプロンプト"
        assert app._language == "en"
        assert app._max_duration == 30.0
        assert app._min_duration_ms == 1000.0
        assert app._hotkey_config == ["shift"]

    def test_app_state_change_callback_wired(self):
        """on_state_change が HotkeyManager に正しく渡される"""
        callback_called = []

        def callback(is_recording):
            callback_called.append(is_recording)

        app = App(on_state_change=callback)
        # HotkeyManager に on_state_change が設定されている
        assert app._hotkey._on_state_change is callback

    def test_app_components_are_wired_together(self):
        """各コンポーネントが正しく相互接続されている"""
        app = App()

        # HotkeyManager が正しい依存を受け取っている
        assert app._hotkey._recorder is app._recorder
        assert app._hotkey._transcriber is app._transcriber
        assert app._hotkey._injector is app._injector

        # Recorder が AudioBuffer を共有している
        assert app._recorder._buffer is app._buffer

    def test_app_run_background_stop_background_idempotent(self):
        """stop_background を2回呼んでも安全"""
        listener = FakeListener()
        app = App()

        app.run_background(listener_factory=lambda **kwargs: listener)
        app.stop_background()
        app.stop_background()  # 2回目: listener は既に None

        # 例外が発生しないこと
        assert True

    def test_end_to_end_via_listener(self):
        """FakeListener 経由でホットキーイベントをシミュレート"""
        buf = AudioBuffer()
        rec = Recorder(buf, stream_factory=lambda *, callback: None)
        trans = FakeTranscriberForApp()
        inj = Injector()
        mgr = HotkeyManager(rec, trans, inj)

        listener = FakeListener(on_press=mgr.on_press, on_release=mgr.on_release)

        # ホットキー押下・解放をシミュレート
        listener.on_press(Key.ctrl_l)
        listener.on_press(Key.alt)
        listener.on_release(Key.alt)

        # App.run は join でブロックするので、ここでは単体で検証
        assert trans.loaded is False  # このテストでは load していない

    def test_app_accepts_glossary_param(self):
        """glossary パラメータが App に受け入れられ HotkeyManager に渡される。"""
        from kikitori.glossary import Glossary
        glossary = Glossary()
        app = App(glossary=glossary)
        assert app._hotkey._glossary is glossary

    def test_app_glossary_none_by_default(self):
        """glossary 未指定時は None で HotkeyManager に渡される。"""
        app = App()
        assert app._hotkey._glossary is None


class TestAppRunWithDI:
    """依存注入を使った App.run のテスト"""

    def test_app_run_uses_custom_listener_factory(self):
        """listener_factory が正しく使われる"""
        factory_called = []

        def factory(**kwargs):
            factory_called.append(kwargs)
            return FakeListener(**kwargs)

        app = App()
        app.run(listener_factory=factory)

        # factory が on_press/on_release を受け取っている
        assert len(factory_called) == 1
        assert "on_press" in factory_called[0]
        assert "on_release" in factory_called[0]
        # HotkeyManager のメソッドが渡されている（bound method は毎回再生成されるので
        # __func__ と __self__ で同一性を確認）
        actual_press = factory_called[0]["on_press"]
        actual_release = factory_called[0]["on_release"]
        assert actual_press is not None
        assert actual_release is not None
        assert actual_press.__func__ is app._hotkey.on_press.__func__
        assert actual_press.__self__ is app._hotkey
        assert actual_release.__func__ is app._hotkey.on_release.__func__
        assert actual_release.__self__ is app._hotkey
