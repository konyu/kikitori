# 07 — Custom Hotkey

## 目的
Option 以外のホットキーを設定可能にする（例: F13, Ctrl+Shift, Cmd+Space）。

## Python 版参照
`kikitori/config.py`:
```python
DEFAULT_HOTKEY: list[str] = ["option"]
```

`kikitori/hotkey_manager.py:resolve_hotkey()`:
```python
def resolve_hotkey(names: list[str]) -> list[list]:
    # 各名前をキーグループに変換
    # 例: ["ctrl", "shift"] → [[Key.ctrl_l, Key.ctrl_r], [Key.shift, Key.shift_r]]
    # 例: ["f13"] → [[Key.f13]]
    # 例: ["cmd", "space"] → [[Key.cmd, Key.cmd_r], [Key.space]]
    key_map = {
        "ctrl": [Key.ctrl_l, Key.ctrl_r],
        "alt": [Key.alt, Key.alt_r],
        "cmd": [Key.cmd, Key.cmd_r],
        "shift": [Key.shift, Key.shift_r],
    }
    # 各グループから1つでも押されていれば「そのキーが押された」と判定
    # 全グループの条件を満たしたらホットキー成立
```

### Python 版のホットキー検知ロジック
- 各グループの `key_id` 集合を作成（O(1) ルックアップ）
- `_pressed_keys` セットで現在押下中のキーを管理
- `_all_hotkey_pressed()`: 全グループが `_pressed_keys` との共通集合を持つかチェック
- `on_press()`: ホットキー関連キー押下 → 全キーが揃ったら録音開始
- `on_release()`: ホットキー関連キー解放 → 全キーが揃わなくなったら録音停止

## Swift 実装仕様

### HotkeyConfig データ型
```swift
public enum Hotkey: Equatable, Sendable {
    case option                          // デフォルト
    case modifiers([HotkeyModifier])     // 修飾キーのみ（Option 以外）
    case key(modifiers: [HotkeyModifier], key: HotkeyKey)  // 修飾キー＋文字キー
}

public enum HotkeyModifier: String, CaseIterable, Sendable {
    case ctrl, alt, cmd, shift
}

public enum HotkeyKey: Equatable, Sendable {
    case character(Character)  // a-z, 0-9
    case space, tab, escape
    case f1...f20
}
```

### 設定文字列パーサー
```swift
public enum HotkeyConfig {
    public static func parse(from names: [String]) -> Hotkey
    // ["option"] → .option
    // ["ctrl"] → .modifiers([.ctrl])
    // ["cmd", "a"] → .key(modifiers: [.cmd], key: .character("a"))
    // ["f13"] → .key(modifiers: [], key: .f13)
    // 未知のキー名 → .option にフォールバック
}
```

### HotkeyManager 拡張
```swift
public var hotkey: Hotkey = .option

private func handle(_ e: NSEvent) {
    switch hotkey {
    case .option:
        // 既存の Option 検知
    case .modifiers(let mods):
        // flagsChanged のみ監視
    case .key(let mods, let key):
        // keyDown/keyUp + flagsChanged を監視
    }
}
```

### NSEvent キーコードマッピング
| キー | keyCode |
|-----|---------|
| A-Z | 0-25 (kVK_ANSI_A = 0) |
| 0-9 | 29-38 (kVK_ANSI_0 = 29) |
| Space | 49 (kVK_Space) |
| Tab | 48 (kVK_Tab) |
| Escape | 53 (kVK_Escape) |
| F1-F12 | 122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111 |
| F13-F20 | 105, 107, 113, 106, 64, 79, 80, 90 |

### 設定ファイル
```yaml
hotkey:
  - ctrl
  - shift
# または
hotkey:
  - f13
# または
hotkey:
  - cmd
  - space
```

### 単体テスト
- 全修飾キー組み合わせのパース
- 文字キー付きパース
- 未知キー名のフォールバック
- 実際のキー押下 → onKeyDown/onKeyUp 発火
