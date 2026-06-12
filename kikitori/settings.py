"""設定ファイル管理と macOS ユーティリティ関数。

設定ファイルの読み書き、フォーカスアプリケーションの取得/復帰などの
macOS 固有のユーティリティを提供する。
"""
from pathlib import Path

SETTINGS_PATH = Path.home() / ".kikitori" / "settings.yaml"


def load_settings() -> dict:
    """設定ファイルを読み込んで辞書で返す。存在しない場合は空辞書。"""
    import yaml
    if SETTINGS_PATH.exists():
        try:
            return yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
    return {}


def save_settings(settings: dict) -> None:
    """設定辞書を YAML ファイルに保存する。"""
    import yaml
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(
            yaml.dump(settings, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def reset_settings() -> None:
    """設定ファイルを削除してデフォルト値に戻す。"""
    try:
        if SETTINGS_PATH.exists():
            SETTINGS_PATH.unlink()
    except Exception:
        pass


def get_frontmost_pid() -> int | None:
    """現在フォーカスされているアプリケーションの PID を取得する。

    macOS 専用。AppKit が利用できない場合は None を返す。
    """
    try:
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return int(app.processIdentifier())
    except Exception:
        return None


def activate_app_by_pid(pid: int) -> bool:
    """指定した PID のアプリケーションをアクティブにする。

    macOS 専用。成功したら True、失敗したら False を返す。
    """
    try:
        from AppKit import NSRunningApplication
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is None:
            return False
        NSApplicationActivateAllWindows = 1 << 0
        NSApplicationActivateIgnoringOtherApps = 1 << 1
        app.activateWithOptions_(
            NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps
        )
        return True
    except Exception:
        return False
