"""デバッグ用エントリポイント — キーイベントのログを追加"""
from kikitori.app import App
from kikitori.hotkey_manager import HotkeyManager, _key_id

_original_on_press = HotkeyManager.on_press
_original_on_release = HotkeyManager.on_release


def _debug_on_press(self, key):
    kid = _key_id(key)
    print(
        f"[DEBUG on_press] key={key!r}, "
        f"_key_id={kid!r}, "
        f"in_hotkey_set={kid in self._hotkey_set}, "
        f"is_recording={self._is_recording}"
    )
    return _original_on_press(self, key)


def _debug_on_release(self, key):
    kid = _key_id(key)
    print(
        f"[DEBUG on_release] key={key!r}, "
        f"_key_id={kid!r}, "
        f"in_hotkey_set={kid in self._hotkey_set}, "
        f"is_recording={self._is_recording}"
    )
    return _original_on_release(self, key)


HotkeyManager.on_press = _debug_on_press
HotkeyManager.on_release = _debug_on_release

app = App()
app.run()
