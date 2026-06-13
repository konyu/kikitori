import Foundation
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

        if let keyName, let kc = keyCodeMap[keyName] {
            return .key(modifiers: modifiers, keyCode: kc)
        }

        if !modifiers.isEmpty {
            return .modifiers(modifiers)
        }

        // パース失敗 → デフォルト
        return .modifiers([.fn])
    }

    // MARK: - Key Code Map

    /// キー名 → macOS virtual key code
    static let keyCodeMap: [String: UInt16] = {
        var map: [String: UInt16] = [:]

        // a-z: kVK_ANSI_A (0) to kVK_ANSI_Z (25)
        for (i, char) in "abcdefghijklmnopqrstuvwxyz".enumerated() {
            map[String(char)] = UInt16(i)
        }

        // 0-9: kVK_ANSI_0 (29) to kVK_ANSI_9 (38)
        for (i, char) in "0123456789".enumerated() {
            map[String(char)] = UInt16(i + 29)
        }

        // Special keys
        map["space"] = 49    // kVK_Space
        map["tab"] = 48      // kVK_Tab
        map["escape"] = 53   // kVK_Escape
        map["return"] = 36   // kVK_Return
        map["delete"] = 51   // kVK_Delete
        map["up"] = 126      // kVK_UpArrow
        map["down"] = 125    // kVK_DownArrow
        map["left"] = 123    // kVK_LeftArrow
        map["right"] = 124   // kVK_RightArrow

        // F1-F20
        let fKeys: [UInt16] = [122, 120, 99, 118, 96, 97, 98, 100, 101, 109,
                               103, 111, 105, 107, 113, 106, 64, 79, 80, 90]
        for (i, code) in fKeys.enumerated() {
            map["f\(i + 1)"] = code
        }

        return map
    }()
}

// MARK: - Hotkey Modifier

public enum HotkeyModifier: String, CaseIterable, Sendable {
    case fn, ctrl, alt, cmd, shift
    // "option" は config 文字列としては .option case にマップされる

    /// ユーザー向け表示名
    var displayName: String {
        switch self {
        case .fn:    return "Fn"
        case .ctrl:  return "Control ⌃"
        case .alt:   return "Option ⌥"
        case .cmd:   return "Command ⌘"
        case .shift: return "Shift ⇧"
        }
    }

    /// NSEvent.ModifierFlags の対応フラグ
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
            return mods.reduce([]) { $0.union($1.flag) }
        }
    }

    /// この設定でキーコード監視が必要か
    var needsKeyMonitoring: Bool {
        if case .key = self { return true }
        return false
    }
}
