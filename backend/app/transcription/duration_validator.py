from __future__ import annotations


class VideoTooLongError(ValueError):
    """Raised when a video exceeds the configured maximum duration."""

    def __init__(self, duration_seconds: int, max_seconds: int) -> None:
        self.duration_seconds = duration_seconds
        self.max_seconds = max_seconds
        super().__init__(
            f"Video duration {duration_seconds}s exceeds the maximum allowed "
            f"{max_seconds}s ({max_seconds // 60} minutes)."
        )


def validate_duration(duration_seconds: int, max_seconds: int) -> None:
    """Raise VideoTooLongError if duration exceeds max. Handles None/zero gracefully."""
    if not duration_seconds:
        return
    if duration_seconds > max_seconds:
        raise VideoTooLongError(duration_seconds, max_seconds)
