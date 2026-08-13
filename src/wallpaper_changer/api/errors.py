class ProviderError(RuntimeError):
    """A wallpaper provider returned an unusable response."""


class DownloadError(RuntimeError):
    """A wallpaper could not be downloaded or validated."""
