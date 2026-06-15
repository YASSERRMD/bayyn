from unittest.mock import MagicMock, patch

import pytest

from app.source_adapters.youtube import YouTubeSourceAdapter, _parse_vtt


def test_youtube_adapter_validates_youtube_url():
    adapter = YouTubeSourceAdapter("https://www.youtube.com/watch?v=test")
    assert adapter.validate_url() is True


def test_youtube_adapter_rejects_non_youtube():
    adapter = YouTubeSourceAdapter("https://vimeo.com/12345")
    assert adapter.validate_url() is False


def test_parse_vtt_extracts_segments():
    vtt = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello world

00:00:05.000 --> 00:00:08.000
This is a test
"""
    segments = _parse_vtt(vtt)
    assert len(segments) == 2
    assert segments[0]["start"] == 1.0
    assert segments[0]["end"] == 4.0
    assert "Hello world" in segments[0]["text"]


def test_parse_vtt_strips_html_tags():
    vtt = """WEBVTT

00:00:01.000 --> 00:00:04.000
<c.colorCCCCCC>Hello</c> <i>world</i>
"""
    segments = _parse_vtt(vtt)
    assert len(segments) == 1
    assert "<" not in segments[0]["text"]
    assert "Hello" in segments[0]["text"]


def test_youtube_metadata_duration_limit():
    adapter = YouTubeSourceAdapter("https://www.youtube.com/watch?v=test")
    mock_info = {
        "title": "Long Video",
        "duration": 999999,
        "language": "en",
        "uploader": "Test",
    }
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="duration"):
            adapter.get_metadata()


def test_youtube_no_captions_returns_empty_list():
    adapter = YouTubeSourceAdapter("https://www.youtube.com/watch?v=test")
    mock_info = {"subtitles": {}, "automatic_captions": {}}

    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = adapter.get_captions()
    assert result == []
