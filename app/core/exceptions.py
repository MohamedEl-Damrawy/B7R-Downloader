"""Application-specific exceptions."""


class VeloError(Exception):
    """Base application error."""


class UnsupportedSourceError(VeloError):
    """URL/source is not supported for authorized download."""


class MetadataExtractionError(VeloError):
    """Failed to extract media metadata."""


class DownloadError(VeloError):
    """Download failed."""


class CancelledError(VeloError):
    """Operation cancelled by user or system."""
