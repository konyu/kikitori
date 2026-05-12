#!/usr/bin/env python3
"""
Voice to Text Injection Tool
Apple Silicon Mac向け音声認識ツール

ホットキー（Ctrl + Option）押下中にマイク入力を録音し、
解放時に音声認識結果をクリップボード経由でペーストします。
"""

import sys
import threading
import time
from typing import List

import numpy as np
import pyperclip
import sounddevice as sd
from pynput import keyboard
from pynput.keyboard import Controller, Key

import mlx_whisper

# ── 設定 ──
SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_NAME = "mlx-community/whisper-large-v3-turbo"
HOTKEY_PROMPT = "以下は日本語の音声認識結果です。"
LANGUAGE = "ja"

# ── グローバル状態 ──
recording = False
audio_buffer: List[np.ndarray] = []
lock = threading.Lock()
keyboard_controller = Controller()
model = None


def load_model():
    """起動時にモデルをプリロードする"""
    global model
    print(f"[INFO] モデルを読み込み中: {MODEL_NAME}")
    model = mlx_whisper.load_models.load_model(MODEL_NAME)
    print("[INFO] モデル読み込み完了")


def start_recording():
    """録音開始"""
    global recording, audio_buffer
    with lock:
        recording = True
        audio_buffer = []
    print("[INFO] 録音開始")


def stop_recording() -> np.ndarray:
    """録音停止して音声データを返す"""
    global recording
    with lock:
        recording = False
        if not audio_buffer:
            return np.array([], dtype=np.float32)
        audio = np.concatenate(audio_buffer, axis=0)
        audio_buffer.clear()
    print("[INFO] 録音停止")
    return audio


def audio_callback(indata, frames, time_info, status):
    """sounddevice コールバック: 録音中のみバッファに蓄積"""
    if status:
        print(f"[WARN] オーディオステータス: {status}", file=sys.stderr)
    with lock:
        if recording:
            # indata shape: (frames, channels)
            audio_buffer.append(indata.copy().reshape(-1))


def transcribe_audio(audio: np.ndarray) -> str:
    """mlx-whisper で音声認識を実行"""
    if audio.size == 0:
        return ""
    print("[INFO] 音声認識中...")
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=MODEL_NAME,
        initial_prompt=HOTKEY_PROMPT,
        language=LANGUAGE,
        verbose=False,
    )
    text = result.get("text", "").strip()
    print(f"[INFO] 認識結果: {text}")
    return text


def inject_text(text: str):
    """クリップボード経由でテキストをペースト"""
    if not text:
        print("[WARN] 空テキストのためペーストをスキップ")
        return
    pyperclip.copy(text)
    print("[INFO] クリップボードにコピーしました")
    # クリップボード反映待ち（長めに）
    time.sleep(0.2)
    print("[INFO] Cmd+V を送信します...")
    
    # 方法1: pynput で送信（アクセシビリティ権限があれば動作）
    try:
        keyboard_controller.press(Key.cmd_l)
        keyboard_controller.press("v")
        keyboard_controller.release("v")
        keyboard_controller.release(Key.cmd_l)
        print("[INFO] pynput でペースト送信完了")
    except Exception as e:
        print(f"[WARN] pynput での送信に失敗: {e}")
    
    # 方法2: AppleScript で送信（別の権限経路を使う）
    try:
        import subprocess
        script = 'delay 0.1\ntell application "System Events" to keystroke "v" using {command down}'
        subprocess.run(["osascript", "-e", script], check=True)
        print("[INFO] AppleScript でペースト送信完了")
    except Exception as e:
        print(f"[WARN] AppleScript での送信に失敗: {e}")
        print("[HINT] アクセシビリティ権限が必要です。システム設定 > プライバシーとセキュリティ > アクセシビリティ を確認してください")


def on_press(key):
    """キー押下時: Ctrl + Option で録音開始"""
    try:
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.alt:
            # 現在の修飾キー状態を確認
            with lock:
                if not recording:
                    # Ctrl と Option(Alt) の両方が押されているか確認
                    # pynput では現在の押下状態を直接取得できないため、
                    # 別途フラグで管理
                    pass
    except Exception as e:
        print(f"[ERROR] on_press: {e}", file=sys.stderr)


def on_release(key):
    """キー解放時: 録音停止・認識・出力"""
    pass


class HotkeyHandler:
    """Ctrl + Option の押下/解放を管理"""

    def __init__(self):
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.stream = None

    def _start_stream(self):
        """マイク入力ストリームを開始"""
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=audio_callback,
        )
        self.stream.start()

    def _stop_stream(self):
        """マイク入力ストリームを停止"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def on_press(self, key):
        if key == keyboard.Key.ctrl_l:
            self.ctrl_pressed = True
        elif key == keyboard.Key.alt:
            self.alt_pressed = True

        if self.ctrl_pressed and self.alt_pressed and not recording:
            self._start_stream()
            start_recording()

    def on_release(self, key):
        with lock:
            was_recording = recording

        if key == keyboard.Key.ctrl_l:
            self.ctrl_pressed = False
        elif key == keyboard.Key.alt:
            self.alt_pressed = False

        if was_recording and not (self.ctrl_pressed and self.alt_pressed):
            self._stop_stream()
            audio = stop_recording()
            if audio.size > 0:
                text = transcribe_audio(audio)
                inject_text(text)
            else:
                print("[INFO] 録音データが空です")


def main():
    print("=" * 50)
    print("Voice to Text Injection Tool")
    print("=" * 50)
    print(f"モデル: {MODEL_NAME}")
    print(f"サンプリングレート: {SAMPLE_RATE} Hz")
    print(f"ホットキー: Ctrl + Option (押下中録音 / 解放で出力)")
    print("=" * 50)

    load_model()

    handler = HotkeyHandler()
    print("[INFO] ホットキーリスナーを開始します。Ctrl+C で終了。")

    with keyboard.Listener(on_press=handler.on_press, on_release=handler.on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
