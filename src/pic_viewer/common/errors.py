"""Domain-specific errors for PicViewer."""


class ImageLoadError(Exception):
    """Raised when an image file cannot be loaded."""


class ImageProcessError(Exception):
    """Raised when image processing fails."""
