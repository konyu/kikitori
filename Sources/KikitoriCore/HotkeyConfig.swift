import AppKit

// MARK: - Hotkey Config

/// ホットキー設定の型
public enum HotkeyConfig: Equatable, Sendable {
    /// Option キー単体（デフォルト）
    case option
    /// 修飾キーのみの組み合わせ（例: Ctrl+Shift）
    case modifiers(Set<HotkeyModifier>)
    /// 修飾キー＋文字キー／ファンクションキー
    case key(modifiers: Set<HotkeyModifier>, keyCode: UInt16)

    /// 文字列配列からパース（例: ["option"], ["ctrl", "shift"], ["f13"]）
    public static func parse(from names: [String]) -> HotkeyConfig {
        guard !names.isEmpty else { return .modifiers([.fn]) }

        // "option" → .option
        if names.count == 1 && names[0].lowercased() == "option" {
            return .option
        }

        var modifiers = Set<HotkeyModifier>()
        var keyName: String?

        for name in names {
            if let mod = HotkeyModifier(rawValue: name.lowercased()) {
                modifiers.insert(mod)
            } else {
                keyName = name.lowercased()
            }
        }

        if let keyName, let kc = Self.keyCode(for: keyName) {
            return .key(modifiers: modifiers, keyCode: kc)
        }

        if !modifiers.isEmpty {
            return .modifiers(modifiers)
        }

        // パース失敗 → デフォルト
        return .modifiers([.fn])
    }

    // MARK: - Key Code Lookup

    /// キー名 → macOS virtual key code（a-z, 0-9 は計算、それ以外はテーブル引き）
    static func keyCode(for name: String) -> UInt16? {
        // 単一文字 a-z / 0-9 はパターンで計算
        if name.utf8.count == 1, let ch = name.utf8.first {
            switch ch {
            case 0x61...0x7A: return UInt16(ch - 0x61)       // a-z → 0-25
            case 0x30...0x39: return UInt16(ch - 0x30 + 29)   // 0-9 → 29-38
            default: break
            }
        }
        // 特殊キー・ファンクションキー
        return specialKeyCodes[name]
    }

    private static let specialKeyCodes: [String: UInt16] = [
        "space": 49, "tab": 48, "escape": 53, "return": 36, "delete": 51,
        "up": 126, "down": 125, "left": 123, "right": 124,
        "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96,
        "f6": 97, "f7": 98, "f8": 100, "f9": 101, "f10": 109,
        "f11": 103, "f12": 111, "f13": 105, "f14": 107, "f15": 113,
        "f16": 106, "f17": 64, "f18": 79, "f19": 80, "f20": 90,
    ]
}

// MARK: - Hotkey Modifier

public enum HotkeyModifier: String, Sendable {
    case fn, ctrl, alt, cmd, shift

    var flag: NSEvent.ModifierFlags {
        switch self {
        case .fn:    return .function
        case .ctrl:  return .control
        case .alt:   return .option
        case .cmd:   return .command
        case .shift: return .shift
        }
    }
}

// MARK: - HotkeyManager Extensions

extension HotkeyConfig {
    /// この設定で使われる全修飾キーフラグ
    var modifierFlags: NSEvent.ModifierFlags {
        switch self {
        case .option: return .option
        case .modifiers(let mods), .key(let mods, _):
            return mods.reduce(into: NSEvent.ModifierFlags()) { $0.formUnion($1.flag) }
        }
    }

    /// この設定でキーコード監視が必要か
    var needsKeyMonitoring: Bool {
        if case .key = self { return true }
        return false
    }
}
