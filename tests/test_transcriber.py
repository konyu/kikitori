"""Transcriber のテスト — 音声認識ラッパー"""
import numpy as np
import pytest

from voice_to_text.transcriber import Transcriber


def fake_transcribe(audio, *, path_or_hf_repo, initial_prompt, language, verbose):
    return {"text": f"prompt={initial_prompt} lang={language} len={len(audio)}"}


def fake_load_model(name):
    return f"model:{name}"


class TestTranscriber:
    def test_load_model_calls_loader(self):
        loaded = []

        def loader(name):
            loaded.append(name)
            return f"loaded:{name}"

        tr = Transcriber("test-model", load_model_func=loader)
        tr.load()
        assert loaded == ["test-model"]
        assert tr._model == "loaded:test-model"

    def test_transcribe_empty_audio_returns_empty(self):
        tr = Transcriber("test-model", transcribe_func=fake_transcribe)
        assert tr.transcribe(np.array([])) == ""

    def test_transcribe_passes_correct_params(self):
        tr = Transcriber(
            "test-model",
            transcribe_func=fake_transcribe,
            load_model_func=fake_load_model,
        )
        tr.load()
        audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        text = tr.transcribe(audio, prompt="テスト", language="en")
        assert text == "prompt=テスト lang=en len=3"

    def test_transcribe_strips_whitespace(self):
        def stub(audio, **kwargs):
            return {"text": "  こんにちは  "}

        tr = Transcriber("m", transcribe_func=stub)
        audio = np.array([1.0], dtype=np.float32)
        assert tr.transcribe(audio) == "こんにちは"

    def test_transcribe_uses_defaults(self):
        calls = []

        def stub(audio, *, path_or_hf_repo, initial_prompt, language, verbose):
            calls.append({
                "path": path_or_hf_repo,
                "prompt": initial_prompt,
                "language": language,
            })
            return {"text": "ok"}

        tr = Transcriber("my-model", transcribe_func=stub)
        audio = np.array([1.0], dtype=np.float32)
        tr.transcribe(audio)
        assert calls[0]["path"] == "my-model"
        assert calls[0]["language"] == "ja"
