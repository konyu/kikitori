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
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        mock_request = MagicMock()
        mock_request_cls.alloc.return_value.init.return_value = mock_request

        mock_task = MagicMock()
        mock_recognizer.recognitionTaskWithRequest_resultHandler_.return_value = mock_task

        sa = SpeechAnalyzer()
        sa.start()

        assert sa._task is mock_task
        mock_request.setRequiresOnDeviceRecognition_.assert_called_once_with(True)

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    def test_start_request_none_calls_error(self, mock_request_cls, mock_sfsr):
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer
        mock_request_cls.alloc.return_value.init.return_value = None

        errors = []
        sa = SpeechAnalyzer()
        sa.on_error = errors.append
        sa.start()

        assert len(errors) == 1
        assert "SFSpeechAudioBufferRecognitionRequest" in errors[0]

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    def test_stop_calls_end_audio_and_cancel(self, mock_request_cls, mock_sfsr):
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        mock_request = MagicMock()
        mock_request_cls.alloc.return_value.init.return_value = mock_request

        mock_task = MagicMock()
        mock_recognizer.recognitionTaskWithRequest_resultHandler_.return_value = mock_task

        sa = SpeechAnalyzer()
        sa.start()
        sa.stop()

        mock_request.endAudio.assert_called_once()
        mock_task.cancel.assert_called_once()
        assert sa._request is None
        assert sa._task is None

    @patch("kikitori.apple_speech.AVAudioFormat")
    @patch("kikitori.apple_speech.AVAudioPCMBuffer")
    def test_append_audio_empty_returns_early(self, mock_buffer_cls, mock_format_cls):
        sa = SpeechAnalyzer()
        sa._request = MagicMock()
        sa.append_audio(np.array([], dtype=np.float32))
        mock_format_cls.assert_not_called()

    @patch("kikitori.apple_speech.AVAudioFormat")
    @patch("kikitori.apple_speech.AVAudioPCMBuffer")
    def test_append_audio_success(self, mock_buffer_cls, mock_format_cls):
        mock_fmt = MagicMock()
        mock_format_cls.return_value = mock_fmt

        mock_buffer = MagicMock()
        mock_buffer_cls.alloc.return_value.initWithPCMFormat_frameCapacity_.return_value = mock_buffer

        import struct
        fake_bytes = struct.pack('3f', 0.1, 0.2, 0.3)

        class FakeChannelPtr:
            def as_buffer(self, n):
                return fake_bytes

        mock_channel_data = MagicMock()
        mock_channel_data.__getitem__.return_value = FakeChannelPtr()
        mock_buffer.floatChannelData.return_value = mock_channel_data

        sa = SpeechAnalyzer()
        sa._request = MagicMock()

        audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        sa.append_audio(audio)

        mock_buffer.setFrameLength_.assert_called_once_with(3)
        sa._request.appendAudioPCMBuffer_.assert_called_once_with(mock_buffer)

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    def test_result_handler_final_result(self, mock_request_cls, mock_sfsr):
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        mock_request = MagicMock()
        mock_request_cls.alloc.return_value.init.return_value = mock_request

        captured_handler = None

        def capture_handler(request, handler):
            nonlocal captured_handler
            captured_handler = handler
            return MagicMock()

        mock_recognizer.recognitionTaskWithRequest_resultHandler_.side_effect = capture_handler

        finals = []
        sa = SpeechAnalyzer()
        sa.on_final_result = finals.append
        sa.start()

        mock_result = MagicMock()
        mock_best = MagicMock()
        mock_best.formattedString.return_value = "最終結果"
        mock_result.bestTranscription.return_value = mock_best
        mock_result.isFinal.return_value = True

        captured_handler(mock_result, None)

        assert finals == ["最終結果"]

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    def test_result_handler_partial_result(self, mock_request_cls, mock_sfsr):
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        mock_request = MagicMock()
        mock_request_cls.alloc.return_value.init.return_value = mock_request

        captured_handler = None

        def capture_handler(request, handler):
            nonlocal captured_handler
            captured_handler = handler
            return MagicMock()

        mock_recognizer.recognitionTaskWithRequest_resultHandler_.side_effect = capture_handler

        partials = []
        sa = SpeechAnalyzer()
        sa.on_partial_result = partials.append
        sa.start()

        mock_result = MagicMock()
        mock_best = MagicMock()
        mock_best.formattedString.return_value = "途中結果"
        mock_result.bestTranscription.return_value = mock_best
        mock_result.isFinal.return_value = False

        captured_handler(mock_result, None)

        assert partials == ["途中結果"]

    @patch("kikitori.apple_speech.SFSpeechRecognizer")
    @patch("kikitori.apple_speech.SFSpeechAudioBufferRecognitionRequest")
    def test_result_handler_none_best_transcription(self, mock_request_cls, mock_sfsr):
        mock_recognizer = MagicMock()
        mock_sfsr.alloc.return_value.initWithLocale_.return_value = mock_recognizer

        mock_request = MagicMock()
        mock_request_cls.alloc.return_value.init.return_value = mock_request

        captured_handler = None

        def capture_handler(request, handler):
            nonlocal captured_handler
            captured_handler = handler
            return MagicMock()

        mock_recognizer.recognitionTaskWithRequest_resultHandler_.side_effect = capture_handler

        partials = []
        finals = []
        sa = SpeechAnalyzer()
        sa.on_partial_result = partials.append
        sa.on_final_result = finals.append
        sa.start()

        mock_result = MagicMock()
        mock_result.bestTranscription.return_value = None

        captured_handler(mock_result, None)

        assert partials == []
        assert finals == []
