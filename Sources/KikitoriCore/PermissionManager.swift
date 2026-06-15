import AVFoundation
import Speech

/// マイク・音声認識権限を管理するユーティリティ。
public final class PermissionManager: @unchecked Sendable {
    public static let shared = PermissionManager()

    private init() {}

    /// マイク権限の現在の状態
    public var microphoneStatus: PermissionStatus {
        switch AVAudioApplication.shared.recordPermission {
        case .undetermined:
            return .notDetermined
        case .denied:
            return .denied
        case .granted:
            return .authorized
        @unknown default:
            return .notDetermined
        }
    }

    /// 音声認識権限の現在の状態
    public var speechRecognitionStatus: PermissionStatus {
        switch SFSpeechRecognizer.authorizationStatus() {
        case .notDetermined:
            return .notDetermined
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .authorized:
            return .authorized
        @unknown default:
            return .notDetermined
        }
    }

    /// マイク権限がなければ許可を求めるダイアログを表示する。
    /// - Returns: 許可後の状態
    @discardableResult
    public func requestMicrophonePermission() async -> PermissionStatus {
        await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { granted in
                continuation.resume(returning: granted ? .authorized : .denied)
            }
        }
    }

    /// 音声認識権限がなければ許可を求めるダイアログを表示する。
    /// - Returns: 許可後の状態
    @discardableResult
    public func requestSpeechRecognitionPermission() async -> PermissionStatus {
        await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: PermissionStatus(status))
            }
        }
    }
}

/// 権限状態を表す列挙型。
public enum PermissionStatus: Sendable {
    case authorized
    case denied
    case notDetermined
    case restricted

    init(_ status: SFSpeechRecognizerAuthorizationStatus) {
        switch status {
        case .notDetermined:
            self = .notDetermined
        case .denied:
            self = .denied
        case .restricted:
            self = .restricted
        case .authorized:
            self = .authorized
        @unknown default:
            self = .notDetermined
        }
    }

    /// ユーザーに許可を求める必要があるか
    public var needsRequest: Bool {
        self == .notDetermined
    }

    /// 機能を利用できるか
    public var isAuthorized: Bool {
        self == .authorized
    }
}
