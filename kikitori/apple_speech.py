"""Apple Speech Framework による音声認識"""
import threading
import time
from typing import Callable

import numpy as np

# PyObjC は実行環境でのみ利用可能
try:
    from AVFoundation import AVAudioFormat, AVAudioPCMBuffer
    from Foundation import NSLocale
    from Speech import (
        SFSpeechAudioBufferRecognitionRequest,
        SFSpeechRecognizer,
        SFSpeechRecognitionResult,
    )
except ImportError:
    AVAudioFormat = None  # type: ignore[misc,assignment]
    AVAudioPCMBuffer = None  # type: ignore[misc,assignment]
    NSLocale = None  # type: ignore[misc,assignment]
    SFSpeechAudioBufferRecognitionRequest = None  # type: ignore[misc,assignment]
    SFSpeechRecognizer = None  # type: ignore[misc,assignment]
    SFSpeechRecognitionResult = None  # type: ignore[misc,assignment]


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
        if SFSpeechRecognizer is None:
            raise RuntimeError("Apple Speech Framework (PyObjC) が利用できません。")

        if self._request_auth:
            auth_event = threading.Event()
            auth_status = [None]

            def _auth_handler(status: int) -> None:
                auth_status[0] = status
                auth_event.set()

            SFSpeechRecognizer.requestAuthorization_(_auth_handler)
            auth_event.wait(timeout=10.0)

        locale = NSLocale.alloc().initWithLocaleIdentifier_(self._locale)
        recognizer = SFSpeechRecognizer.alloc().initWithLocale_(locale)
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
        import sys

        from kikitori.config import BENCHMARK_MODE as _BM
        _t0 = time.perf_counter()

        if audio.size == 0:
            return ""

        if self._recognizer is None:
            return ""

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)
        if fmt is None:
            return ""

        buffer = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(
            fmt, len(audio)
        )
        if buffer is None:
            return ""

        buffer.setFrameLength_(len(audio))

        float_data = buffer.floatChannelData()
        if float_data is None:
            return ""

        channel_ptr = float_data[0]
        if channel_ptr is None:
            return ""

        try:
            # np.frombuffer は read-only 配列を返すのでコピーが必要
            buf = channel_ptr.as_buffer(len(audio))
            np_buf = np.frombuffer(buf, dtype=np.float32).copy()
            np_buf[:] = audio[:len(np_buf)]
        except Exception:
            return ""

        request = SFSpeechAudioBufferRecognitionRequest.alloc().init()
        if request is None:
            return ""

        request.setRequiresOnDeviceRecognition_(self._on_device)
        request.setAddsPunctuation_(True)
        request.appendAudioPCMBuffer_(buffer)
        request.endAudio()

        done_event = threading.Event()
        transcription = [""]

        def _result_handler(
            result: SFSpeechRecognitionResult | None, error: object
        ) -> None:
            if error is not None:
                transcription[0] = ""
                done_event.set()
                return

            if result is not None:
                best = result.bestTranscription()
                if best is not None:
                    text = best.formattedString()
                    transcription[0] = text if text is not None else ""

                if transcription[0] or result.isFinal():
                    done_event.set()
            else:
                transcription[0] = ""
                done_event.set()

        task = self._recognizer.recognitionTaskWithRequest_resultHandler_(
            request, _result_handler
        )
        if task is None:
            return ""

        # 部分結果を任意のスレッドから待つ。done_event は最初のテキスト到着でセット。
        # テキストが来なければ100ms待つ。来たら即返す。
        done_event.wait(timeout=0.10)

        result_text = transcription[0]

        if _BM:
            elapsed = (time.perf_counter() - _t0) * 1000
            print(f"[BENCH] apple_speech_transcribe: {elapsed:.1f}ms "
                  f"(audio_len={len(audio)} frames)", flush=True)

        return result_text


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
        self._request = None
        self._task = None

        # SFSpeechRecognizer はメインスレッドで作成する必要がある。
        # __init__ は App.__init__ からメインスレッドで呼ばれる。
        locale_obj = NSLocale.alloc().initWithLocaleIdentifier_(self._locale)
        self._recognizer = SFSpeechRecognizer.alloc().initWithLocale_(locale_obj)

        self.on_partial_result: Callable[[str], None] | None = None
        self.on_final_result: Callable[[str], None] | None = None
        self.on_error: Callable[[str], None] | None = None

    def start(self) -> None:
        """音声認識セッションを開始する。メインスレッドから呼ぶこと。

        新しい SFSpeechAudioBufferRecognitionRequest を作成し、
        事前に作成済みの SFSpeechRecognizer で認識タスクを開始する。
        """
        import sys
        from Foundation import NSThread
        if not NSThread.isMainThread():
            print("[WARN] SpeechAnalyzer.start() is not on main thread", file=sys.stderr)

        if self._task is not None:
            self.stop()

        if self._recognizer is None:
            if self.on_error is not None:
                self.on_error("SFSpeechRecognizer が初期化されていません")
            return

        request = SFSpeechAudioBufferRecognitionRequest.alloc().init()
        if request is None:
            if self.on_error is not None:
                self.on_error(
                    "SFSpeechAudioBufferRecognitionRequest の作成に失敗しました"
                )
            return

        request.setRequiresOnDeviceRecognition_(self._on_device)
        request.setAddsPunctuation_(True)
        self._request = request

        def _result_handler(
            result: SFSpeechRecognitionResult | None, error: object
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
        """音声認識セッションを完全に終了する。

        end_audio → cancel の順で実行する。
        """
        self.end_audio()
        self.cancel()

    def end_audio(self) -> None:
        """音声入力の終了を通知する。

        認識タスクはキャンセルせず、最終結果コールバックを待つ。
        """
        if self._request is not None:
            self._request.endAudio()

    def cancel(self) -> None:
        """認識タスクをキャンセルしてリソースを解放する。"""
        if self._request is not None:
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

        fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)
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
            buf = channel_ptr.as_buffer(len(audio))
            np_buf = np.frombuffer(buf, dtype=np.float32).copy()
            np_buf[:] = audio[:len(np_buf)]
        except Exception:
            return

        self._request.appendAudioPCMBuffer_(buffer)
