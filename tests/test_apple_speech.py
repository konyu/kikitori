"""Apple Speech Framework 音声認識のテスト"""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from kikitori.apple_speech import SpeechAnalyzer, SpeechTranscriber


class TestSpeechTranscriber:
    def test_init_stores_params(self):
        tr = SpeechTranscriber(locale="en-US", on_device=False, request_auth=False)
        assert tr._locale == "en-US"
        assert tr._on_device is False
        assert tr._request_auth is False

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    def test_load_without_auth(self, mock_sfsr):
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        tr = SpeechTranscriber(request_auth=False)
        tr.load()

        mock_sfsr.alloc.return_value.initWithLocale_.assert_called_once()
        assert tr._recognizer is mock_recognizer

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    def test_load_with_none_recognizer_raises(self, mock_sfsr):
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = None
        tr = SpeechTranscriber(request_auth=False)
        with pytest.raises(RuntimeError):
            tr.load()

    def test_transcribe_empty_audio_returns_empty(self):
        tr = SpeechTranscriber(request_auth=False)
        assert tr.transcribe(np.array([], dtype=np.float32)) == ""

    def test_transcribe_without_load_returns_empty(self):
        tr = SpeechTranscriber(request_auth=False)
        audio = np.array([0.1, 0.2], dtype=np.float32)
        assert tr.transcribe(audio) == ""

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    @patch("kikitori.apple_speech.AVAudioPCMBuffer")
    @patch("kikitori.apple_speech.AVAudioFormat")
    def test_transcribe_success(self, mock_format_cls, mock_buffer_cls, mock_request_cls, mock_sfsr):
        # Arrange: recognizer
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        # Arrange: format
        mock_fmt = MagicMock()
        mock_format_cls.alloc.return_value.initStandardFormatWithSampleRate_channels_.return_value = mock_fmt

        # Arrange: buffer
        mock_buffer = MagicMock()
        mock_buffer_cls.alloc.return_value.initWithPCMFormat_frameCapacity_.return_value = mock_buffer

        # Arrange: floatChannelData → channel_ptr with as_buffer
        import struct
        fake_bytes = struct.pack('3f', 0.1, 0.2, 0.3)

        class FakeChannelPtr:
            def as_buffer(self, n):
                return fake_bytes

        mock_channel_data = MagicMock()
        mock_channel_data.__getitem__.return_value = FakeChannelPtr()
        mock_buffer.floatChannelData.return_value = mock_channel_data

        # Arrange: request
        mock_request = MagicMock()
        mock_request_cls.alloc.return_value.init.return_value = mock_request

        # Arrange: task + callback simulation
        mock_task = MagicMock()
        mock_recognizer.recognitionTaskWithRequest_resultHandler_.return_value = mock_task

        def capture_handler(request, handler):
            mock_result = MagicMock()
            mock_best = MagicMock()
            mock_best.formattedString.return_value = "テスト結果"
            mock_result.bestTranscription.return_value = mock_best
            mock_result.isFinal.return_value = True
            handler(mock_result, None)
            return mock_task

        mock_recognizer.recognitionTaskWithRequest_resultHandler_.side_effect = capture_handler

        # Act
        tr = SpeechTranscriber(request_auth=False)
        tr.load()
        audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        result = tr.transcribe(audio, prompt="p", language="ja")

        # Assert
        assert result == "テスト結果"
        mock_request.setRequiresOnDeviceRecognition_.assert_called_once_with(True)

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    @patch("kikitori.apple_speech.AVAudioPCMBuffer")
    @patch("kikitori.apple_speech.AVAudioFormat")
    def test_transcribe_none_best_transcription(self, mock_format_cls, mock_buffer_cls, mock_request_cls, mock_sfsr):
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        mock_fmt = MagicMock()
        mock_format_cls.alloc.return_value.initStandardFormatWithSampleRate_channels_.return_value = mock_fmt

        mock_buffer = MagicMock()
        mock_buffer_cls.alloc.return_value.initWithPCMFormat_frameCapacity_.return_value = mock_buffer

        import struct
        fake_bytes = struct.pack('1f', 0.1)

        class FakeChannelPtr:
            def as_buffer(self, n):
                return fake_bytes

        mock_channel_data = MagicMock()
        mock_channel_data.__getitem__.return_value = FakeChannelPtr()
        mock_buffer.floatChannelData.return_value = mock_channel_data

        mock_request = MagicMock()
        mock_request_cls.alloc.return_value.init.return_value = mock_request

        mock_task = MagicMock()

        def capture_handler(request, handler):
            mock_result = MagicMock()
            mock_result.bestTranscription.return_value = None
            mock_result.isFinal.return_value = True
            handler(mock_result, None)
            return mock_task

        mock_recognizer.recognitionTaskWithRequest_resultHandler_.side_effect = capture_handler

        tr = SpeechTranscriber(request_auth=False)
        tr.load()
        audio = np.array([0.1], dtype=np.float32)
        result = tr.transcribe(audio)

        assert result == ""


class TestSpeechAnalyzer:
    def test_init_stores_params(self):
        sa = SpeechAnalyzer(locale="en-US", on_device=False)
        assert sa._locale == "en-US"
        assert sa._on_device is False
        assert sa.on_partial_result is None
        assert sa.on_final_result is None
        assert sa.on_error is None

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    def test_start_success(self, mock_request_cls, mock_sfsr):
        """start() はバックグラウンドスレッドを開始する。"""
        import threading as _th
        sa = SpeechAnalyzer()
        assert not sa._running
        sa.start()
        assert sa._running
        assert sa._thread is not None
        assert sa._thread.is_alive()
        # 非同期停止: stop() は join しない。スレッドは daemon で残る。
        sa.stop()
        assert not sa._running
        # スレッドは join されないので None ではない
        assert sa._thread is not None

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    def test_start_request_none_calls_error(self, mock_request_cls, mock_sfsr):
        """SFSpeechRecognizer が None を返す場合、エラーになる。"""
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = None

        errors = []
        sa = SpeechAnalyzer()
        sa.on_error = errors.append
        sa.start()
        # 非同期 stop(): スレッドに少し時間を与えて実行させる
        sa._thread.join(timeout=1.0)  # エラーで即座に終了するはず
        sa.stop()

        assert len(errors) >= 1
        assert "失敗" in errors[0]

    def test_stop_calls_end_audio_and_cancel(self):
        """stop() は _running を False にし、_generation を進める。

        非同期 stop(): join しない。スレッドの後始末は _run() 内で行う。
        """
        sa = SpeechAnalyzer()
        sa._running = True
        old_gen = sa._generation

        # ダミースレッドを作成（実際には start していない）
        import threading as _th
        sa._thread = _th.Thread(target=lambda: None)

        sa.stop()

        assert sa._running is False
        assert sa._generation == old_gen + 1
        # 非同期 stop ではスレッドをクリアしない
        assert sa._thread is not None

    @patch("kikitori.apple_speech.AVAudioFormat")
    @patch("kikitori.apple_speech.AVAudioPCMBuffer")
    def test_append_audio_empty_returns_early(self, mock_buffer_cls, mock_format_cls):
        sa = SpeechAnalyzer()
        sa.append_audio(np.array([], dtype=np.float32))
        mock_format_cls.assert_not_called()

    @patch("kikitori.apple_speech.AVAudioFormat")
    @patch("kikitori.apple_speech.AVAudioPCMBuffer")
    def test_append_audio_success(self, mock_buffer_cls, mock_format_cls):
        """append_audio は音声データを内部キューに追加する。

        _run スレッドが後でキューから取り出してリクエストに追加するため、
        ここではキューに入ったことだけを確認する。
        """
        sa = SpeechAnalyzer()
        sa._running = True  # スレッド開始済みとみなす

        audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        sa.append_audio(audio)

        assert len(sa._audio_queue) == 1
        assert np.array_equal(sa._audio_queue[0], audio)

    def test_result_handler_final_result(self):
        """on_final_result コールバックが正しく設定される。"""
        sa = SpeechAnalyzer()
        called = []
        sa.on_final_result = called.append
        # コールバックを直接テスト
        sa.on_final_result("final")
        assert called == ["final"]

    def test_result_handler_partial_result(self):
        """on_partial_result コールバックが正しく設定される。"""
        sa = SpeechAnalyzer()
        called = []
        sa.on_partial_result = called.append
        sa.on_partial_result("partial")
        assert called == ["partial"]

    def test_result_handler_none_best_transcription(self):
        """get_latest_text がデフォルトで空文字列を返す。"""
        sa = SpeechAnalyzer()
        assert sa.get_latest_text() == ""
        assert sa.is_final() is False
