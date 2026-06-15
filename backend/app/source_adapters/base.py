from abc import ABC, abstractmethod


class BaseSourceAdapter(ABC):
    """Abstract base for all URL source adapters."""

    def __init__(self, url: str) -> None:
        self.url = url

    @abstractmethod
    def validate_url(self) -> bool:
        """Return True if the URL is valid for this adapter."""

    @abstractmethod
    def get_metadata(self) -> dict:
        """Return dict with title, duration, language, thumbnail_url (not stored)."""

    @abstractmethod
    def get_captions(self) -> list[dict]:
        """
        Return list of caption segments as dicts:
        [{"start": float, "end": float, "text": str}, ...]
        Returns empty list if no captions available.
        """

    @abstractmethod
    def get_audio_stream_url(self) -> str:
        """Return URL to best audio stream for transcription. Never store this."""


class TwitterXSourceAdapter(BaseSourceAdapter):
    """Placeholder for Twitter/X video support."""

    def validate_url(self) -> bool:
        raise NotImplementedError("TwitterX adapter not yet implemented.")

    def get_metadata(self) -> dict:
        raise NotImplementedError

    def get_captions(self) -> list[dict]:
        raise NotImplementedError

    def get_audio_stream_url(self) -> str:
        raise NotImplementedError


class VimeoSourceAdapter(BaseSourceAdapter):
    """Placeholder for Vimeo support."""

    def validate_url(self) -> bool:
        raise NotImplementedError("Vimeo adapter not yet implemented.")

    def get_metadata(self) -> dict:
        raise NotImplementedError

    def get_captions(self) -> list[dict]:
        raise NotImplementedError

    def get_audio_stream_url(self) -> str:
        raise NotImplementedError


class PodcastRSSSourceAdapter(BaseSourceAdapter):
    """Placeholder for Podcast RSS feed support."""

    def validate_url(self) -> bool:
        raise NotImplementedError("Podcast RSS adapter not yet implemented.")

    def get_metadata(self) -> dict:
        raise NotImplementedError

    def get_captions(self) -> list[dict]:
        raise NotImplementedError

    def get_audio_stream_url(self) -> str:
        raise NotImplementedError


class DirectMP4SourceAdapter(BaseSourceAdapter):
    """Placeholder for direct MP4 URL support."""

    def validate_url(self) -> bool:
        raise NotImplementedError("Direct MP4 adapter not yet implemented.")

    def get_metadata(self) -> dict:
        raise NotImplementedError

    def get_captions(self) -> list[dict]:
        return []

    def get_audio_stream_url(self) -> str:
        raise NotImplementedError
