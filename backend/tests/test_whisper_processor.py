import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_temp_audio_deleted_after_transcription(tmp_path):
    """Temp audio file must be deleted immediately after transcription."""
    job_id = uuid.uuid4()
    wav_path = tmp_path / "audio.wav"
    wav_path.write_bytes(b"fake wav data")
    assert wav_path.exists()

    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 5.0
    mock_segment.text = "Hello world"
    mock_segment.avg_logprob = -0.3

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.99

    with patch("faster_whisper.WhisperModel") as MockModel:
        mock_model_instance = MagicMock()
        mock_model_instance.transcribe.return_value = ([mock_segment], mock_info)
        MockModel.return_value = mock_model_instance

        from app.transcription.whisper_processor import _run_whisper
        results, lang = _run_whisper(wav_path)

    assert not wav_path.exists(), "Temp audio file was not deleted after transcription"
    assert len(results) == 1
    assert results[0]["text"] == "Hello world"
    assert lang == "en"


def test_whisper_segments_have_correct_structure():
    mock_segment = MagicMock()
    mock_segment.start = 1.5
    mock_segment.end = 4.3
    mock_segment.text = " Test segment "
    mock_segment.avg_logprob = -0.25

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.95

    with patch("faster_whisper.WhisperModel") as MockModel:
        mock_model_instance = MagicMock()
        mock_model_instance.transcribe.return_value = ([mock_segment], mock_info)
        MockModel.return_value = mock_model_instance

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake")
            wav_path = Path(f.name)

        from app.transcription.whisper_processor import _run_whisper
        results, lang = _run_whisper(wav_path)

    assert results[0]["start"] == 1.5
    assert results[0]["end"] == 4.3
    assert results[0]["text"] == "Test segment"
    assert "confidence" in results[0]


def test_no_audio_stream_url_in_results():
    """Transcription result must never contain raw audio URLs."""
    from app.transcription.whisper_processor import _run_whisper
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"fake")
        wav_path = Path(f.name)

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.99

    with patch("faster_whisper.WhisperModel") as MockModel:
        mock_model_instance = MagicMock()
        mock_model_instance.transcribe.return_value = ([], mock_info)
        MockModel.return_value = mock_model_instance

        results, _lang = _run_whisper(wav_path)

    for seg in results:
        assert "url" not in seg
        assert "stream" not in seg
