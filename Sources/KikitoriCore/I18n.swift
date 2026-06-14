import Foundation

/// UI 表示言語
public enum Language: String, Sendable {
    case ja, en
}

/// 翻訳キー
public enum TranslationKey: Int, Sendable {
    // Menu
    case menuSettings = 0, menuCorrections, menuQuit

    // Status
    case statusIdle, statusRecording

    // Errors
    case errorModelFailed, errorRecordFailed

    // Log
    case logModelReady, listenerStarted, emptyAudio, tooShort, silence

    // Settings
    case settingsTitle, tabGeneral, tabFilters
    case settingsLanguageLabel, settingsUILanguageLabel
    case settingsHotkeyLabel, settingsMinDurLabel, settingsMaxDurLabel, settingsRmsLabel, settingsDebugLabel
    case settingsMinDurHint
    case settingsResetBtn, settingsCancelBtn, settingsSaveBtn, btnClose
    case msUnit, secUnit
    
    // Corrections
    case correctionsTitle, correctionsInstruction
    case correctionsOpenFile, correctionsReload
    case correctionsWrongCol, correctionsRightCol
    case btnAdd, btnEdit, btnDelete
    case correctionsAddTitle, correctionsEditTitle
    case correctionsWrongLabel, correctionsRightLabel
}

/// 多言語対応マネージャー
@MainActor
public final class I18n: ObservableObject {
    @Published public private(set) var language: Language

    /// システム言語から自動判定して初期化
    public init(language: Language? = nil) {
        self.language = language ?? Self.detectOSLanguage()
    }
    
    public func setLanguage(_ code: String?) {
        if let code = code, let l = Language(rawValue: code) {
            self.language = l
        } else {
            self.language = Self.detectOSLanguage()
        }
    }

    /// 翻訳文字列を取得
    public func t(_ key: TranslationKey) -> String {
        switch language {
        case .ja: return Self._lookup(key, Self.jaStrings)
        case .en: return Self._lookup(key, Self.enStrings)
        }
    }

    // MARK: - 文字列テーブル（TranslationKey.rawValue でインデックス）

    private nonisolated static let jaStrings: [String] = [
        "設定",                             // menuSettings
        "校正設定...",                       // menuCorrections
        "終了",                             // menuQuit
        "待機中",                           // statusIdle
        "録音中",                           // statusRecording
        "音声認識の初期化に失敗",             // errorModelFailed
        "録音開始失敗",                      // errorRecordFailed
        "音声認識の準備完了",                // logModelReady
        "ホットキーリスナーを開始",          // listenerStarted
        "録音データが空です",                // emptyAudio
        "録音が短すぎます",                  // tooShort
        "無音と判定されました",              // silence
        "Kikitori 設定",                    // settingsTitle
        "一般",                             // tabGeneral
        "フィルタ",                         // tabFilters
        "認識言語:",                        // settingsLanguageLabel
        "UI 表示言語:",                     // settingsUILanguageLabel
        "ホットキー（修飾キーの組み合わせ）:", // settingsHotkeyLabel
        "最低録音時間:",                    // settingsMinDurLabel
        "最大録音時間:",                    // settingsMaxDurLabel
        "無音判定 RMS:",                    // settingsRmsLabel
        "デバッグログ",                      // settingsDebugLabel
        "これより短い録音は無視されます",     // settingsMinDurHint
        "デフォルトに戻す",                  // settingsResetBtn
        "キャンセル",                       // settingsCancelBtn
        "保存",                             // settingsSaveBtn
        "閉じる",                           // btnClose
        "ms",                               // msUnit
        "秒",                               // secUnit
        "校正設定 (Corrections)",           // correctionsTitle
        "yaml形式で置換ルールを記述します。左に音声認識の誤変換、右に正しい単語を記述してください。", // correctionsInstruction
        "ファイルを開く",                    // correctionsOpenFile
        "再読み込み",                       // correctionsReload
        "間違い (変換前)",                   // correctionsWrongCol
        "訂正 (変換後)",                     // correctionsRightCol
        "追加",                             // btnAdd
        "編集",                             // btnEdit
        "削除",                             // btnDelete
        "ペアを追加",                        // correctionsAddTitle
        "ペアを編集",                        // correctionsEditTitle
        "間違い (例: use effect):",          // correctionsWrongLabel
        "訂正 (例: useEffect):",             // correctionsRightLabel
    ]

    private nonisolated static let enStrings: [String] = [
        "Settings",
        "Corrections...",
        "Quit",
        "Idle",
        "Recording",
        "Speech recognition init failed",
        "Recording start failed",
        "Speech recognition ready",
        "Hotkey listener started",
        "Recording data is empty",
        "Recording too short",
        "Detected as silence",
        "Kikitori Settings",
        "General",
        "Filters",
        "Recognition language:",
        "UI language:",
        "Hotkey (Modifiers):",
        "Min duration:",
        "Max duration:",
        "Silence RMS:",
        "Debug Log",
        "Shorter recordings are ignored",
        "Reset Defaults",
        "Cancel",
        "Save",
        "Close",
        "ms",
        "sec",
        "Corrections",
        "Write replacement rules in yaml format. Place the misrecognized word on the left and the correct word on the right.",
        "Open File",
        "Reload",
        "Wrong (Before)",
        "Right (After)",
        "Add",
        "Edit",
        "Delete",
        "Add Pair",
        "Edit Pair",
        "Wrong (e.g. use effect):",
        "Right (e.g. useEffect):",
    ]

    private nonisolated static func _lookup(_ key: TranslationKey, _ arr: [String]) -> String {
        let idx = key.rawValue
        guard idx < arr.count else { return "\(key)" }
        let s = arr[idx]
        return s.isEmpty ? "\(key)" : s
    }

    // MARK: - OS 言語検出

    public static func detectOSLanguage() -> Language {
        guard let first = Locale.preferredLanguages.first else { return .en }
        if first.hasPrefix("ja") { return .ja }
        // 今後 zh, ko 等を追加可能
        return .en
    }
}
