import Foundation

/// UI 表示言語
public enum Language: String, CaseIterable, Sendable {
    case ja, en
}

/// 翻訳キー
public enum TranslationKey: String, CaseIterable, Sendable {
    // Menu
    case menuSettings, menuCorrections, menuQuit

    // Status
    case statusIdle, statusRecording

    // Errors
    case errorModelFailed, errorRecordFailed

    // Log
    case logModelReady, listenerStarted, emptyAudio, tooShort, silence

    // Settings
    case settingsTitle
    case tabGeneral, tabFilters
    case settingsLanguageLabel, settingsUILanguageLabel
    case settingsHotkeyLabel, settingsMinDurLabel, settingsMaxDurLabel, settingsRmsLabel, settingsDebugLabel
    case settingsMinDurHint
    case settingsResetBtn, settingsCancelBtn, settingsSaveBtn, btnClose
    case msUnit, secUnit
    
    // Corrections
    case correctionsTitle
    case correctionsInstruction
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

    /// 現在の言語設定
    public var currentLanguage: Language { language }

    /// 翻訳文字列を取得
    public func t(_ key: TranslationKey) -> String {
        Self.strings[language]?[key] ?? Self.strings[.ja]?[key] ?? key.rawValue
    }

    // MARK: - 文字列辞書

    private static let strings: [Language: [TranslationKey: String]] = [
        .ja: [
            .menuSettings: "設定",
            .menuCorrections: "校正設定...",
            .menuQuit: "終了",
            .statusIdle: "待機中",
            .statusRecording: "録音中",
            .errorModelFailed: "音声認識の初期化に失敗",
            .errorRecordFailed: "録音開始失敗",
            .logModelReady: "音声認識の準備完了",
            .listenerStarted: "ホットキーリスナーを開始",
            .emptyAudio: "録音データが空です",
            .tooShort: "録音が短すぎます",
            .silence: "無音と判定されました",
            .settingsTitle: "Kikitori 設定",
            .tabGeneral: "一般",
            .tabFilters: "フィルタ",
            .settingsLanguageLabel: "認識言語:",
            .settingsUILanguageLabel: "UI 表示言語:",
            .settingsHotkeyLabel: "ホットキー（修飾キーの組み合わせ）:",
            .settingsMinDurLabel: "最低録音時間:",
            .settingsMaxDurLabel: "最大録音時間:",
            .settingsRmsLabel: "無音判定 RMS:",
            .settingsDebugLabel: "デバッグログ",
            .settingsMinDurHint: "これより短い録音は無視されます",
            .settingsResetBtn: "デフォルトに戻す",
            .settingsCancelBtn: "キャンセル",
            .settingsSaveBtn: "保存",
            .btnClose: "閉じる",
            .msUnit: "ms",
            .secUnit: "秒",
            .correctionsTitle: "校正設定 (Corrections)",
            .correctionsInstruction: "yaml形式で置換ルールを記述します。左に音声認識の誤変換、右に正しい単語を記述してください。",
            .correctionsOpenFile: "ファイルを開く",
            .correctionsReload: "再読み込み",
            .correctionsWrongCol: "間違い (変換前)",
            .correctionsRightCol: "訂正 (変換後)",
            .btnAdd: "追加",
            .btnEdit: "編集",
            .btnDelete: "削除",
            .correctionsAddTitle: "ペアを追加",
            .correctionsEditTitle: "ペアを編集",
            .correctionsWrongLabel: "間違い (例: use effect):",
            .correctionsRightLabel: "訂正 (例: useEffect):",
        ],
        .en: [
            .menuSettings: "Settings",
            .menuCorrections: "Corrections...",
            .menuQuit: "Quit",
            .statusIdle: "Idle",
            .statusRecording: "Recording",
            .errorModelFailed: "Speech recognition init failed",
            .errorRecordFailed: "Recording start failed",
            .logModelReady: "Speech recognition ready",
            .listenerStarted: "Hotkey listener started",
            .emptyAudio: "Recording data is empty",
            .tooShort: "Recording too short",
            .silence: "Detected as silence",
            .settingsTitle: "Kikitori Settings",
            .tabGeneral: "General",
            .tabFilters: "Filters",
            .settingsLanguageLabel: "Recognition language:",
            .settingsUILanguageLabel: "UI language:",
            .settingsHotkeyLabel: "Hotkey (Modifiers):",
            .settingsMinDurLabel: "Min duration:",
            .settingsMaxDurLabel: "Max duration:",
            .settingsRmsLabel: "Silence RMS:",
            .settingsDebugLabel: "Debug Log",
            .settingsMinDurHint: "Shorter recordings are ignored",
            .settingsResetBtn: "Reset Defaults",
            .settingsCancelBtn: "Cancel",
            .settingsSaveBtn: "Save",
            .btnClose: "Close",
            .msUnit: "ms",
            .secUnit: "sec",
            .correctionsTitle: "Corrections",
            .correctionsInstruction: "Write replacement rules in yaml format. Place the misrecognized word on the left and the correct word on the right.",
            .correctionsOpenFile: "Open File",
            .correctionsReload: "Reload",
            .correctionsWrongCol: "Wrong (Before)",
            .correctionsRightCol: "Right (After)",
            .btnAdd: "Add",
            .btnEdit: "Edit",
            .btnDelete: "Delete",
            .correctionsAddTitle: "Add Pair",
            .correctionsEditTitle: "Edit Pair",
            .correctionsWrongLabel: "Wrong (e.g. use effect):",
            .correctionsRightLabel: "Right (e.g. useEffect):",
        ],
    ]

    // MARK: - OS 言語検出

    public static func detectOSLanguage() -> Language {
        guard let first = Locale.preferredLanguages.first else { return .en }
        if first.hasPrefix("ja") { return .ja }
        // 今後 zh, ko 等を追加可能
        return .en
    }
}
