import Foundation

/// UI 表示言語
public enum Language: String, Sendable {
    case ja, en
}

/// 翻訳キー
public enum TranslationKey: Int, Sendable, CaseIterable {
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
    case settingsMinDurHint, settingsLaunchAtLogin
    case settingsResetBtn, settingsCancelBtn, settingsSaveBtn, btnClose
    case msUnit, secUnit
    
    // Corrections
    case correctionsTitle, correctionsInstruction
    case correctionsOpenFile, correctionsReload
    case correctionsWrongCol, correctionsRightCol
    case btnAdd, btnEdit, btnDelete
    case correctionsAddTitle, correctionsEditTitle
    case correctionsWrongLabel, correctionsRightLabel
    
    // Updates
    case menuCheckUpdates

    // Permissions
    case permissionDeniedTitle, permissionDeniedMessage, permissionOpenSettings, permissionOK

    // Accessibility Dialog
    case axPermissionTitle, axPermissionMessage, axPermissionStep1, axPermissionStep2, axPermissionStep3, axPermissionCopied, btnDoNotShowAgain
}

/// 多言語対応マネージャー
@MainActor
public final class I18n: ObservableObject {
    @Published public private(set) var language: Language

    /// 現在選択されている言語（テスト互換用のエイリアス）
    public var currentLanguage: Language { language }

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
        "Mac起動時にKikitoriを開く",         // settingsLaunchAtLogin
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
        
        "アップデートを確認...",              // menuCheckUpdates

        // Permissions
        "権限が必要です",
        "Kikitori を使うにはマイクと音声認識へのアクセスを許可してください。",
        "システム設定を開く",
        "OK",

        // Accessibility Dialog
        "アクセシビリティの許可が必要です",
        "Kikitoriが自動的にテキストを入力できるようにするには、システム設定でアクセシビリティの許可を付与してください：",
        "1. システム設定 → プライバシーとセキュリティ → アクセシビリティを開く（パスワードやTouch IDでのロック解除が必要な場合があります）",
        "2. 「＋」ボタンをクリックし、アプリケーションフォルダからKikitoriを選択して「開く」をクリック",
        "3. Kikitoriの横のチェックボックスがオンになっていることを確認",
        "テキストは自動的にクリップボードにコピーされました。文字起こし後もペーストできます。",
        "今後表示しない"
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
        "Launch Kikitori at login",
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
        
        "Check for Updates...",              // menuCheckUpdates

        // Permissions
        "Permission Required",
        "Please allow Kikitori to access the microphone and speech recognition.",
        "Open System Settings",
        "OK",

        // Accessibility Dialog
        "Accessibility Permission Required",
        "To allow Kikitori to type text automatically, please grant Accessibility permission in System Settings:",
        "1. Open System Settings → Privacy & Security → Accessibility (you may need to unlock with a password or Touch ID)",
        "2. Click the '+' button, navigate to the Applications folder, select Kikitori, and click 'Open'",
        "3. Ensure the checkbox next to Kikitori is turned on",
        "The text has been copied to your clipboard. You can paste it manually.",
        "Do not show again"
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
