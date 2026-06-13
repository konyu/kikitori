import Foundation

/// UI 表示言語
public enum Language: String, CaseIterable, Sendable {
    case ja, en
}

/// 翻訳キー
public enum TranslationKey: String, CaseIterable, Sendable {
    // Menu
    case menuSettings, menuQuit

    // Status
    case statusIdle, statusRecording

    // Errors
    case errorModelFailed, errorRecordFailed

    // Log
    case logModelReady, listenerStarted, emptyAudio, tooShort, silence

    // Settings
    case settingsTitle
    case settingsLanguageLabel, settingsUILanguageLabel
    case settingsHotkeyLabel, settingsMinDurLabel, settingsMinDurHint
    case settingsResetBtn, settingsCancelBtn, settingsSaveBtn
}

/// 多言語対応マネージャー
public final class I18n: Sendable {
    private let language: Language

    /// システム言語から自動判定して初期化
    public init(language: Language? = nil) {
        self.language = language ?? Self.detectOSLanguage()
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
            .settingsLanguageLabel: "認識言語:",
            .settingsUILanguageLabel: "UI 表示言語:",
            .settingsHotkeyLabel: "ホットキー:",
            .settingsMinDurLabel: "最低録音時間:",
            .settingsMinDurHint: "これより短い録音は無視されます",
            .settingsResetBtn: "デフォルトに戻す",
            .settingsCancelBtn: "キャンセル",
            .settingsSaveBtn: "保存して適用",
        ],
        .en: [
            .menuSettings: "Settings",
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
            .settingsLanguageLabel: "Recognition language:",
            .settingsUILanguageLabel: "UI language:",
            .settingsHotkeyLabel: "Hotkey:",
            .settingsMinDurLabel: "Min duration:",
            .settingsMinDurHint: "Shorter recordings are ignored",
            .settingsResetBtn: "Reset to Defaults",
            .settingsCancelBtn: "Cancel",
            .settingsSaveBtn: "Save & Apply",
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
