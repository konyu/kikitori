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
            print("[DEBUG] transcribe: recognizer is None", flush=True)
            return ""

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(16000.0, 1)
        if fmt is None:
            print("[DEBUG] transcribe: AVAudioFormat is None", flush=True)
            return ""

        buffer = AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(
            fmt, len(audio)
        )
        if buffer is None:
            print("[DEBUG] transcribe: AVAudioPCMBuffer is None", flush=True)
            return ""

        buffer.setFrameLength_(len(audio))

        float_data = buffer.floatChannelData()
        if float_data is None:
            print("[DEBUG] transcribe: floatChannelData() is None", flush=True)
            return ""

        channel_ptr = float_data[0]
        if channel_ptr is None:
            print("[DEBUG] transcribe: channel_ptr is None", flush=True)
            return ""

        try:
            # np.frombuffer は PCM バッファのメモリを参照するビューを返す。
            # .copy() すると切断された独立配列になるので注意。
            # as_buffer は要素数（float数）を取る
            buf = channel_ptr.as_buffer(len(audio))
            np_buf = np.frombuffer(buf, dtype=np.float32)
            np_buf[:] = audio[:len(np_buf)]
        except Exception as e:
            print(f"[DEBUG] transcribe: buffer copy FAILED: {type(e).__name__}: {e}", flush=True)
            return ""

        request = SFSpeechAudioBufferRecognitionRequest.alloc().init()
        if request is None:
            print("[DEBUG] transcribe: SFSpeechAudioBufferRecognitionRequest is None", flush=True)
            return ""

        request.setRequiresOnDeviceRecognition_(self._on_device)
        request.setAddsPunctuation_(True)
        print(f"[DEBUG] transcribe: on_device={self._on_device}, locale={self._locale}", flush=True)
        request.appendAudioPCMBuffer_(buffer)
        request.endAudio()

        done_event = threading.Event()
        transcription = [""]
        _handler_calls = [0]  # mutable counter for nested function

        def _result_handler(
            result: SFSpeechRecognitionResult | None, error: object
        ) -> None:
            _handler_calls[0] += 1
            call_n = _handler_calls[0]

            if error is not None:
                print(f"[DEBUG] transcribe handler #{call_n}: ERROR={error}", flush=True)
                transcription[0] = ""
                done_event.set()
                return

            if result is not None:
                best = result.bestTranscription()
                text = ""
                is_final = result.isFinal()
                if best is not None:
                    text = best.formattedString() or ""
                print(f"[DEBUG] transcribe handler #{call_n}: text='{text}' isFinal={is_final} result={result}", flush=True)
                if text:
                    transcription[0] = text
                if transcription[0] or is_final:
                    done_event.set()
            else:
                print(f"[DEBUG] transcribe handler #{call_n}: result=None", flush=True)
                transcription[0] = ""
                done_event.set()

        task = self._recognizer.recognitionTaskWithRequest_resultHandler_(
            request, _result_handler
        )
        if task is None:
            print("[DEBUG] transcribe: recognitionTaskWithRequest is None", flush=True)
            return ""

        # 部分結果を任意のスレッドから待つ。done_event は最初のテキスト到着でセット。
        # テキストが来なければ100ms待つ。来たら即返す。
        done_event.wait(timeout=0.10)

        result_text = transcription[0]

        print(f"[DEBUG] transcribe returning: text='{result_text}' handler_calls={_handler_calls[0]}", flush=True)

        if _BM:
            elapsed = (time.perf_counter() - _t0) * 1000
            print(f"[BENCH] apple_speech_transcribe: {elapsed:.1f}ms "
                  f"(audio_len={len(audio)} frames)", flush=True)

        return result_text


class SpeechAnalyzer:
    """Apple Speech Framework を使ったリアルタイム音声認識クラス。

    専用バックグラウンドスレッド上で SFSpeechRecognizer を実行し、
    録音と並行して音声認識を行う。認識結果はコールバックで通知される。

    すべての SFSpeechRecognizer 操作は同一スレッド（専用スレッド）上で
    実行されるため、スレッド間競合が発生しない。
    """

    def __init__(
        self,
        locale: str = "ja-JP",
        on_device: bool = True,
    ):
        self._locale = locale
        self._on_device = on_device

        # スレッド間通信用
        self._audio_queue: list[np.ndarray] = []
        self._audio_lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._generation = 0  # start() ごとにインクリメント、古いスレッドの干渉防止

        # 認識結果
        self._latest_text = ""
        self._is_final = False
        self._text_lock = threading.Lock()

        self.on_partial_result: Callable[[str], None] | None = None
        self.on_final_result: Callable[[str], None] | None = None
        self.on_error: Callable[[str], None] | None = None

    def start(self) -> None:
        """音声認識スレッドを開始する。

        専用スレッド上で SFSpeechRecognizer と認識タスクを作成し、
        そのスレッドの NSRunLoop でコールバックを処理する。
        """
        if self._running:
            return

        self._generation += 1
        self._running = True
        self._latest_text = ""
        self._is_final = False
        self._audio_queue.clear()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """音声認識を停止する。

        スレッドの終了は待たず、即座に戻る。
        daemon スレッドがバックグラウンドで endAudio → 最終結果取得 → 終了を行う。
        古いスレッドの後始末は _generation カウンタで保護される。
        """
        if not self._running:
            return
        self._running = False
        self._generation += 1
        # join しない — daemon スレッドがバックグラウンドで後始末

    def cancel(self) -> None:
        """認識タスクをキャンセルする（stop のシノニム）。"""
        self.stop()

    def end_audio(self) -> None:
        """音声入力の終了を通知する（専用スレッド上で処理）。"""
        pass  # _run ループ内で _running=False を検出して endAudio を呼ぶ

    def append_audio(self, audio: np.ndarray) -> None:
        """音声データを認識キューに追加する。

        スレッドセーフ。録音コールバックから任意のスレッドで呼び出し可能。

        Args:
            audio: 16000Hz、モノラル、float32 の numpy 配列。
        """
        if audio.size == 0:
            return
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        with self._audio_lock:
            self._audio_queue.append(audio.copy())

    def get_latest_text(self) -> str:
        """最新の認識テキストを取得する（スレッドセーフ）。"""
        with self._text_lock:
            return self._latest_text

    def is_final(self) -> bool:
        """最終認識結果が得られたかどうかを返す。"""
        with self._text_lock:
            return self._is_final

    # ----------------------------------------------------------------
    # 専用スレッド
    # ----------------------------------------------------------------

    def _run(self) -> None:
        """専用スレッドのエントリポイント。

        SFSpeechRecognizer を作成し、NSRunLoop を駆動しながら
        音声データを逐次認識リクエストに追加する。

        _generation カウンタで古いスレッドの干渉を防止:
        - stop() → start() で _generation が進むと、古いスレッドは即座にループを抜ける
        - 後始末はローカル変数に対して行い、新スレッドの状態を壊さない
        """
        from Foundation import NSRunLoop, NSDate, NSDefaultRunLoopMode

        my_gen = self._generation

        locale_obj = NSLocale.alloc().initWithLocaleIdentifier_(self._locale)
        recognizer = SFSpeechRecognizer.alloc().initWithLocale_(locale_obj)
        if recognizer is None:
            if self.on_error is not None:
                self.on_error("SFSpeechRecognizer の作成に失敗しました")
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

        # 事前に AVAudioFormat を作成しておく
        fmt = AVAudioFormat.alloc().initStandardFormatWithSampleRate_channels_(
            16000.0, 1
        )

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
            with self._text_lock:
                self._latest_text = text
                self._is_final = is_final

            if is_final:
                if self.on_final_result is not None:
                    self.on_final_result(text)
            else:
                if self.on_partial_result is not None:
                    self.on_partial_result(text)

        task = recognizer.recognitionTaskWithRequest_resultHandler_(
            request, _result_handler
        )
        if task is None:
            if self.on_error is not None:
                self.on_error("認識タスクの開始に失敗しました")
            return

        run_loop = NSRunLoop.currentRunLoop()
        audio_ended = False

        # ループ条件: 記録中 or 音声終了未処理、かつ世代が一致する
        while (self._running or not audio_ended) and self._generation == my_gen:
            # NSRunLoop をポンプ（コールバック処理）
            run_loop.runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.01),
            )

            # 音声データがあれば認識リクエストに追加
            chunks: list[np.ndarray] = []
            with self._audio_lock:
                if self._audio_queue:
                    chunks = self._audio_queue[:]
                    self._audio_queue.clear()

            for chunk in chunks:
                self._append_to_request(request, fmt, chunk)

            # 停止指示が出ていて、まだ endAudio を呼んでいない場合
            if not self._running and not audio_ended:
                request.endAudio()
                audio_ended = True
                # 最終結果を待つ（短い発話なら 200ms で十分）
                deadline = time.perf_counter() + 0.2
                while time.perf_counter() < deadline:
                    run_loop.runMode_beforeDate_(
                        NSDefaultRunLoopMode,
                        NSDate.dateWithTimeIntervalSinceNow_(0.01),
                    )
                    if self._is_final:
                        break

        # 後始末（ローカル変数に対してのみ行い、次世代の状態を壊さない）
        task.cancel()

    @staticmethod
    def _append_to_request(
        request: object,
        fmt: object,
        audio: np.ndarray,
    ) -> None:
        """PCM バッファを作成し、認識リクエストに追加する。

        認識スレッド上で呼ばれることを前提とする（スレッドセーフではない）。
        """
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
            # as_buffer は要素数（float数）を取る
            buf = channel_ptr.as_buffer(len(audio))
            np_buf = np.frombuffer(buf, dtype=np.float32)
            np_buf[:] = audio[:len(np_buf)]
        except Exception:
            return

        request.appendAudioPCMBuffer_(buffer)
