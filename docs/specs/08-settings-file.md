# 08 — Settings File

## 目的
ユーザー設定を YAML ファイルで永続化。次回起動時に復元。

## Python 版参照
`kikitori/settings.py`:
```python
SETTINGS_PATH = Path.home() / ".kikitori" / "settings.yaml"

def load_settings() -> dict:
    import yaml
    if SETTINGS_PATH.exists():
        return yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}

def save_settings(settings: dict) -> None:
    import yaml
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(yaml.dump(settings, allow_unicode=True, ...))

def reset_settings() -> None:
    if SETTINGS_PATH.exists(): SETTINGS_PATH.unlink()
```

`kikitori/config.py`:
```python
DEFAULT_LANGUAGE = "ja"
DEFAULT_UI_LANGUAGE = None  # OS から自動検出
MAX_DURATION = 60.0
MIN_DURATION_MS = 300.0
SILENCE_RMS_THRESHOLD = 0.0001
DEFAULT_HOTKEY = ["option"]
DEBUG = False  # 環境変数 DEBUG で上書き可能
```

## Swift 実装仕様

### ファイルパス
```
~/.kikitori/settings.yaml
```

### YAML 構造
```yaml
language: ja              # 認識言語（ja, en, zh, ko, ...）
ui_language: ja           # UI 言語（ja, en）。未指定時 OS 自動検出
hotkey:                   # ホットキー
  - option
min_duration_ms: 300      # 最低録音時間
max_duration_sec: 60      # 最大録音時間
silence_rms_threshold: 0.0001  # 無音判定 RMS 閾値
debug: false              # デバッグログ
```

### SettingsManager クラス
```swift
public final class SettingsManager: Sendable {
    // 全プロパティはデフォルト値を持ち、設定ファイルで上書き
    
    public private(set) var language: String = "ja"
    public private(set) var uiLanguage: String? = nil
    public private(set) var hotkey: [String] = ["option"]
    public private(set) var minDurationMs: Double = 300.0
    public private(set) var maxDurationSec: Double = 60.0
    public private(set) var silenceRmsThreshold: Double = 0.0001
    public private(set) var debug: Bool = false
    
    public init() { load() }
    
    public func load()    // settings.yaml 読み込み
    public func save()    // settings.yaml 書き込み
    public func reset()   // ファイル削除 → デフォルトに戻す
}
```

### load() 実装
1. `settingsPath` が存在しなければデフォルト値のまま
2. `yaml.safe_load()` または `String(contentsOf:)` + 手動パース
3. 各キーが存在すればプロパティを上書き
4. パースエラー時はデフォルト値を維持 + エラーログ

### save() 実装
1. 親ディレクトリ作成（`~/.kikitori/`）
2. 全プロパティを YAML にシリアライズ
3. アトミック書き込み（temp → rename）

### 依存関係
- YAML パーサー: シンプルな自前実装（キー・値ペアの手動パース）で十分。YamlSwift 等の外部依存不要
- `FileManager.default` を使用

### 単体テスト
- ファイル不在でデフォルト値
- 全キー読み込み
- 部分的なキーのみ読み込み（他はデフォルト）
- 保存→再読み込みで値一致
- reset() でファイル削除 + デフォルト値
