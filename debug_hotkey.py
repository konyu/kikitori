"""ホットキーデバッグスクリプト"""
import time

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from kikitori.hotkey_manager import resolve_hotkey, _key_id

print("=== 1. resolve_hotkey(['option']) の結果 ===")
groups = resolve_hotkey(["option"])
print(f"groups={groups}")

key_set = set()
for group in groups:
    for k in group:
        key_set.add(_key_id(k))
print(f"key_set={key_set}")

print("\n=== 2. Optionキー（Key.alt）の判定 ===")
alt_id = _key_id(Key.alt)
print(f"Key.alt -> _key_id = {alt_id!r}")
print(f"alt_id in key_set: {alt_id in key_set}")

alt_r_id = _key_id(Key.alt_r)
print(f"Key.alt_r -> _key_id = {alt_r_id!r}")
print(f"alt_r_id in key_set: {alt_r_id in key_set}")

print("\n=== 3. 実際のキーイベント捕捉 ===")
print("5秒間、押したキーを表示します。Optionキーを押してください。")

events = []

def on_press(key):
    kid = _key_id(key)
    in_set = kid in key_set
    events.append(("press", key, kid, in_set))
    print(f"  PRESS: key={key!r}, _key_id={kid!r}, in_hotkey_set={in_set}")

def on_release(key):
    kid = _key_id(key)
    in_set = kid in key_set
    events.append(("release", key, kid, in_set))
    print(f"  RELEASE: key={key!r}, _key_id={kid!r}, in_hotkey_set={in_set}")

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()
time.sleep(5)
listener.stop()

print("\n=== 4. イベントサマリー ===")
for ev in events:
    print(f"  {ev[0]}: {ev[1]!r} -> id={ev[2]!r} -> in_set={ev[3]}")
