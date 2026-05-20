"""macOS メニューバー常駐型 Kikitori アプリ（ターミナル実行推奨）"""
import os
import threading
from pathlib import Path

import rumps
import yaml

from kikitori.app import App
from kikitori.config import DEFAULT_HOTKEY, DEFAULT_LANGUAGE, DEFAULT_PROMPT, MIN_DURATION_MS, MODEL_NAME, SAMPLE_RATE, SILENCE_RMS_THRESHOLD
from kikitori.corrections import Corrections, CORRECTIONS_PATH
from kikitori.glossary import Glossary, GLOSSARY_PATH
from kikitori.hotkey_manager import resolve_hotkey

SETTINGS_PATH = Path.home() / ".kikitori_settings.yaml"


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            return yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
    return {}


def save_settings(settings):
    try:
        SETTINGS_PATH.write_text(
            yaml.dump(settings, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except Exception:
        pass


class KikitoriStatusBarApp(rumps.App):
    def __init__(self):
        super().__init__("🎤", title="Kikitori", quit_button=None)

        self._settings = load_settings()
        self._language = self._settings.get("language", DEFAULT_LANGUAGE)
        self._prompt = self._settings.get("prompt", DEFAULT_PROMPT)
        self._hotkey = self._settings.get("hotkey", DEFAULT_HOTKEY)
        self._min_duration_ms = self._settings.get("min_duration_ms", MIN_DURATION_MS)
        self._silence_rms_threshold = self._settings.get("silence_rms_threshold", SILENCE_RMS_THRESHOLD)

        # 専門用語集の読み込み
        self._glossary = Glossary()
        self._glossary.load()

        # Core app with state-change callback
        self._app = App(
            language=self._language,
            prompt=self._prompt,
            hotkey=self._hotkey,
            min_duration_ms=self._min_duration_ms,
            silence_rms_threshold=self._silence_rms_threshold,
            on_state_change=self._on_core_state_change,
            glossary=self._glossary,
        )

        # Menu items
        self._status_item = rumps.MenuItem("○ 待機中")
        self._language_item = rumps.MenuItem(f"言語: {self._language}")
        self._prompt_item = rumps.MenuItem(self._prompt_preview(self._prompt))
        self._prompt_item.set_callback(None)
        self._updated_item = rumps.MenuItem("最終更新: --")
        self._updated_item.set_callback(None)
        self._model_item = rumps.MenuItem(f"モデル: {MODEL_NAME}")
        self._model_item.set_callback(None)
        self._model_loading_item = rumps.MenuItem("モデルを読み込み中...")
        self._model_loading_item.set_callback(None)

        self._hotkey_item = rumps.MenuItem(f"ホットキー: {' + '.join(self._hotkey)}")
        self._hotkey_item.set_callback(None)

        # 録音開始/停止ボタン（メニューからの手動操作用）
        self._record_toggle_item = rumps.MenuItem("🔴 録音開始", callback=self._toggle_recording)

        self.menu = [
            self._status_item,
            None,
            self._record_toggle_item,
            None,
            self._model_loading_item,
            self._language_item,
            self._prompt_item,
            self._updated_item,
            self._model_item,
            self._hotkey_item,
            None,
            rumps.MenuItem("設定ファイルを開く", callback=self._open_settings),
            rumps.MenuItem("設定をデフォルトに戻す", callback=self._reset_settings),
            rumps.MenuItem("用語集ファイルを開く", callback=self._open_glossary),
            rumps.MenuItem("校正辞書ファイルを開く", callback=self._open_corrections),
            None,
            rumps.MenuItem("終了", callback=self._quit_app),
        ]

        # State flags
        self._recording = False
        self._model_ready = False
        self._loading_item_removed = False

        # Pending UI updates
        self._pending_language = None
        self._pending_prompt = None
        self._pending_updated = None

        # Start background loading
        threading.Thread(target=self._load_model, daemon=True).start()

        # Settings watcher
        self._settings_mtime = 0
        self._settings_timer = None

        # Glossary watcher
        self._glossary_mtime = 0

    def _load_model(self):
        """バックグラウンドでモデルを読み込み、完了後にメニューを更新"""
        try:
            self._app.load()
            self._model_ready = True
            if not self._loading_item_removed:
                self._loading_item_removed = True
                self._remove_loading_item()
        except Exception as e:
            print(f"[ERROR] モデル読み込み失敗: {e}", flush=True)

    def _remove_loading_item(self):
        """メインスレッドで安全にメニュー項目を削除"""
        def remove(timer):
            if self._model_loading_item in self.menu:
                self.menu.pop(self._model_loading_item)
        rumps.Timer(remove, 0.5).start()

    def _on_core_state_change(self, is_recording: bool):
        """録音状態変更時にUIを更新"""
        self._recording = is_recording
        if is_recording:
            self.title = "🔴"
            self._status_item.title = "🔴 録音中..."
            self._record_toggle_item.title = "⏹ 録音停止"
        else:
            self.title = "🎤"
            self._status_item.title = "○ 待機中"
            self._record_toggle_item.title = "🔴 録音開始"

    def _prompt_preview(self, prompt: str) -> str:
        """長いプロンプトを省略して表示"""
        if len(prompt) > 20:
            return f"プロンプト: {prompt[:20]}..."
        return f"プロンプト: {prompt}" if prompt else "プロンプト: (未設定)"

    def _start_settings_watcher(self):
        """設定ファイルの変更を監視し、変更があれば自動再読み込み"""
        try:
            self._settings_mtime = os.path.getmtime(SETTINGS_PATH)
        except OSError:
            self._settings_mtime = 0

        def check_settings_change(timer):
            try:
                current_mtime = os.path.getmtime(SETTINGS_PATH)
                if current_mtime != getattr(self, "_settings_mtime", 0):
                    self._settings_mtime = current_mtime
                    self._reload_settings()
            except (OSError, FileNotFoundError):
                pass

        # 既存の watcher があれば停止
        if hasattr(self, "_settings_timer") and self._settings_timer is not None:
            self._settings_timer.stop()
            self._settings_timer = None

        self._settings_timer = rumps.Timer(check_settings_change, 1.0)
        self._settings_timer.start()

    def _reload_settings(self):
        """設定ファイルを再読み込みしてアプリに反映"""
        new_settings = load_settings()
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")

        # 設定ファイルが存在しない場合はデフォルト値に戻す
        if not new_settings:
            new_settings = {
                "language": DEFAULT_LANGUAGE,
                "prompt": DEFAULT_PROMPT,
                "hotkey": DEFAULT_HOTKEY,
                "min_duration_ms": MIN_DURATION_MS,
                "silence_rms_threshold": SILENCE_RMS_THRESHOLD,
            }

        changed = False

        new_lang = new_settings.get("language", DEFAULT_LANGUAGE)
        if new_lang != self._language:
            self._language = new_lang
            self._app._language = new_lang
            self._app._hotkey._language = new_lang
            self._pending_language = f"言語: {new_lang}"
            changed = True

        new_prompt = new_settings.get("prompt", DEFAULT_PROMPT)
        if new_prompt != self._prompt:
            self._prompt = new_prompt
            self._app._prompt = new_prompt
            self._app._hotkey._prompt = new_prompt
            self._pending_prompt = self._prompt_preview(new_prompt)
            changed = True

        new_min_dur = new_settings.get("min_duration_ms", MIN_DURATION_MS)
        if new_min_dur != self._min_duration_ms:
            self._min_duration_ms = new_min_dur
            self._app._min_duration_ms = new_min_dur
            self._app._hotkey._min_duration_samples = int(new_min_dur / 1000 * SAMPLE_RATE)
            changed = True

        new_hotkey = new_settings.get("hotkey", DEFAULT_HOTKEY)
        if new_hotkey != self._hotkey:
            self._hotkey = new_hotkey
            self._app._hotkey_config = new_hotkey
            self._app._hotkey.update_hotkey(new_hotkey)
            self._hotkey_item.title = f"ホットキー: {' + '.join(self._hotkey)}"
            changed = True

        new_silence = new_settings.get("silence_rms_threshold", SILENCE_RMS_THRESHOLD)
        if new_silence != self._silence_rms_threshold:
            self._silence_rms_threshold = new_silence
            self._app._hotkey._silence_rms_threshold = new_silence
            changed = True

        # 用語集ファイルの再読み込み
        self._glossary.load()

        self._settings = new_settings
        if changed:
            self._pending_updated = f"最終更新: {now}"
            self._flash_icon("✅")
            try:
                rumps.notification(
                    "Kikitori",
                    "設定を更新しました",
                    f"言語: {self._language} / {self._prompt_preview(self._prompt)}",
                )
            except RuntimeError:
                pass

    def _flash_icon(self, icon: str, duration: float = 1.5):
        """一時的にアイコンを変更して視覚的フィードバックを与える"""
        original = self.title
        # 録音中なら 🔴 のままにする
        if original == "🔴":
            return
        self.title = icon
        def restore(timer):
            if not self._recording:
                self.title = original
        rumps.Timer(restore, duration).start()

    def _update_ui(self, timer):
        """定期的にメニュー項目を更新（設定変更反映用）"""
        if self._pending_language:
            self._language_item.title = self._pending_language
            self._pending_language = None
        if self._pending_prompt:
            self._prompt_item.title = self._pending_prompt
            self._pending_prompt = None
        if self._pending_updated:
            self._updated_item.title = self._pending_updated
            self._pending_updated = None

    def _toggle_recording(self, _):
        """メニューから録音開始/停止"""
        if self._app._hotkey.is_recording():
            self._app._hotkey.stop_recording()
        else:
            self._app._hotkey.start_recording()

    def _open_settings(self, _):
        """設定ファイルをデフォルトエディタで開く（初回はマニュアル付きで生成）"""
        if not SETTINGS_PATH.exists():
            default_yaml = f"""# Kikitori 設定ファイル
# 設定変更後は自動的に反映されます（再起動不要）

language: {self._language}
prompt: "{self._prompt}"
hotkey:
"""
            for k in self._hotkey:
                default_yaml += f"  - {k}\n"
            default_yaml += f"min_duration_ms: {self._min_duration_ms}\n"
            SETTINGS_PATH.write_text(default_yaml, encoding="utf-8")

        import subprocess
        subprocess.Popen(["open", str(SETTINGS_PATH)])
        self._start_settings_watcher()

    def _reset_settings(self, _):
        """設定をデフォルトに戻してアプリを再起動する。"""
        from kikitori.settings import reset_settings
        reset_settings()
        self._reload_settings()
        try:
            rumps.notification(
                "Kikitori",
                "設定をリセットしました",
                "デフォルト値に戻りました。",
            )
        except RuntimeError:
            pass

    def _open_glossary(self, _):
        """用語集ファイルを開く（存在しない場合は雛形を生成）"""
        if not GLOSSARY_PATH.exists():
            GLOSSARY_PATH.write_text(
                "# 専門用語リスト\n# Whisper の認識精度向上のために使用\n\nterms:\n  - MLX\n  - Transformer\n",
                encoding="utf-8",
            )
        import subprocess
        subprocess.Popen(["open", str(GLOSSARY_PATH)])

    def _open_corrections(self, _):
        """校正辞書ファイルを開く（存在しない場合は雛形を生成）"""
        if not CORRECTIONS_PATH.exists():
            CORRECTIONS_PATH.write_text(
                "# Kikitori 校正辞書\n"
                "# Whisper の音声認識結果に対し、以下の「間違い: 訂正」ペアを自動適用します。\n"
                "# 大文字小文字は無視して置換されます。\n\n"
                "corrections:\n  '間違い例': '訂正例'\n",
                encoding="utf-8",
            )
        import subprocess
        subprocess.Popen(["open", str(CORRECTIONS_PATH)])

    def _quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    KikitoriStatusBarApp().run()
