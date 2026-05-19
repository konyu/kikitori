"""Apple Speech Framework による音声認識"""
import ctypes
import os
import tempfile
import threading
import wave
from typing import Callable

import numpy as np

# PyObjC は実行環境でのみ利用可能
try:
    from AVFoundation import AVAudioFormat, AVAudioPCMBuffer
    from Foundation import NSURL
    from Speech import (
        SFSpeechAudioBufferRecognitionRequest,
        SFSpeechRecognizer,
        SFSpeechRecognitionTaskResult,
        SFSpeechURLRecognitionRequest,
    )
except ImportError:
    AVAudioFormat = None  # type: ignore[misc,assignment]
    AVAudioPCMBuffer = None  # type: ignore[misc,assignment]
    NSURL = None  # type: ignore[misc,assignment]
    SFSpeechAudioBufferRecognitionRequest = None  # type: ignore[misc,assignment]
    SFSpeechRecognizer = None  # type: ignore[misc,assignment]
    SFSpeechRecognitionTaskResult = None  # type: ignore[misc,assignment]
    SFSpeechURLRecognitionRequest = None  # type: ignore[misc,assignment]


class SpeechTranscriber:
    """Apple Speech Framework を使ったバッチ音声認識クラス。

    既存の ``Transcriber`` とダックタイピング互換。
    ``transcribe(audio, prompt="", language="ja") -> str`` インターフェースを提供する。
    """

    def __init__(
        self,
        locale: str = "ja-JP",
        on_device: bool = True,
        request_auth: bool = True,
    ):
        self._locale = locale
        self._on_device = on_device
        self._request_auth = request_auth
        self._recognizer = None

    def load(self) -> None:
        """音声認識の認可をリクエストし、認識エンジンを準備する。

        初回実行時は macOS の音声認識権限ダイアログが表示される可能性がある。
        """
        if self._request_auth:
            auth_event = threading.Event()
            auth_status = [None]

            def _auth_handler(status: int) -> None:
                auth_status[0] = status
                auth_event.set()

            SFSpeechRecognizer.requestAuthorization_(_auth_handler)
            auth_event.wait(timeout=10.0)

        recognizer = SFSpeechRecognizer.alloc().initWithLocale_(self._locale)
        if recognizer is None:
            raise RuntimeError(
                f"SFSpeechRecognizer の作成に失敗しました: locale={self._locale}"
            )
        self._recognizer = recognizer

    def transcribe(
        self,
        audio: np.ndarray,
        prompt: str = "",
        language: str = "ja",
    ) -> str:
        """音声データを一括認識してテキストを返す。

        Args:
            audio: 16000Hz、モノラル、float32 の numpy 配列。
            prompt: Apple Speech では無視される（ダックタイピング互換用）。
            language: Apple Speech では無視される（ダックタイピング互換用）。
                      実際に使用されるロケールは ``__init__`` で指定した値。

        Returns:
            認識結果の文字列。認識失敗時は空文字列。
        """
        if audio.size == 0:
            return ""

        if self._recognizer is None:
            return ""

        # float32 を int16 に変換して一時 WAV ファイルに書き出す
        # （wave モジュールは PCM フォーマットのみ対応のため）
        audio_normalized = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_normalized * 32767.0).astype(np.int16)

        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        try:
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_int16.tobytes())

            file_url = NSURL.fileURLWithPath_(wav_path)
            if file_url is None:
                return ""

            request = SFSpeechURLRecognitionRequest.alloc().initWithURL_(file_url)
            if request is None:
                return ""

            request.setRequiresOnDeviceRecognition_(self._on_device)

            done_event = threading.Event()
            transcription = [""]

            def _result_handler(
                result: SFSpeechRecognitionTaskResult | None, error: object
            ) -> None:
                if error is not None:
                    transcription[0] = ""
                elif result is not None:
                    best = result.bestTranscription()
                    if best is not None:
                        text = best.formattedString()
                        transcription[0] = text if text is not None else ""
                    else:
                        transcription[0] = ""
                else:
                    transcription[0] = ""
                done_event.set()

            task = self._recognizer.recognitionTaskWithRequest_resultHandler_(
                request, _result_handler
            )
            if task is None:
                return ""

            done_event.wait(timeout=60.0)

            return transcription[0]
        finally:
            try:
                os.remove(wav_path)
            except OSError:
                pass


class SpeechAnalyzer:
    """Apple Speech Framework を使ったリアルタイム音声分析クラス。

    録音中に逐次音声認識結果をコールバックで通知する。
    """

    def __init__(
        self,
        locale: str = "ja-JP",
        on_device: bool = True,
    ):
        self._locale = locale
        self._on_device = on_device
        self._recognizer = None
        self._request = None
        self._task = None

        self.on_partial_result: Callable[[str], None] | None = None
        self.on_final_result: Callable[[str], None] | None = None
        self.on_error: Callable[[str], None] | None = None

    def start(self) -> None:
        """音声認識セッションを開始する。

        ``SFSpeechAudioBufferRecognitionRequest`` を作成し、認識タスクを開始する。
        """
        if self._task is not None:
            self.stop()

        recognizer = SFSpeechRecognizer.alloc().initWithLocale_(self._locale)
        if recognizer is None:
            if self.on_error is not None:
                self.on_error(
                    f"SFSpeechRecognizer の作成に失敗しました: locale={self._locale}"
                )
            return

        self._recognizer = recognizer

        request = SFSpeechAudioBufferRecognitionRequest.alloc().init()
        if request is None:
            if self.on_error is not None:
                self.on_error(
                    "SFSpeechAudioBufferRecognitionRequest の作成に失敗しました"
                )
            return

        request.setRequiresOnDeviceRecognition_(self._on_device)
        self._request = request

        def _result_handler(
            result: SFSpeechRecognitionTaskResult | None, error: object
        ) -> None:
            if error is not None:
                if self.on_error is not None:
                    self.on_error(str(error))
                return

            if result is None:
                return

            best = result.bestTranscription()
            if best is None:
                return

            text = best.formattedString()
            if text is None:
                text = ""

            is_final = result.isFinal()
            if is_final:
                if self.on_final_result is not None:
                    self.on_final_result(text)
            else:
                if self.on_partial_result is not None:
                    self.on_partial_result(text)

        self._task = self._recognizer.recognitionTaskWithRequest_resultHandler_(
            request, _result_handler
        )
        if self._task is None:
            if self.on_error is not None:
                self.on_error("認識タスクの開始に失敗しました")

    def stop(self) -> None:
        """音声認識セッションを終了する。

        認識リクエストを終了し、タスクをキャンセルする。
        """
        if self._request is not None:
            self._request.endAudio()
            self._request = None

        if self._task is not None:
            self._task.cancel()
            self._task = None

        self._recognizer = None

    def append_audio(self, audio: np.ndarray) -> None:
        """音声データを認識リクエストに追加する。

        Args:
            audio: 16000Hz、モノラル、float32 の numpy 配列。
        """
        if self._request is None:
            return

        if audio.size == 0:
            return

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        fmt = AVAudioFormat(16000.0, 1)
        if fmt is None:
            return

        buffer = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(
            fmt, len(audio)
        )
        if buffer is None:
            return

        buffer.setFrameLength_(len(audio))

        float_data = buffer.floatChannelData()
        if float_data is None:
            return

        channel_ptr = float_data[0]
        if channel_ptr is None:
            return

        try:
            ctypes.memmove(int(channel_ptr), audio.ctypes.data, audio.nbytes)
        except Exception:
            return

        self._request.appendAudioPCMBuffer_(buffer)
