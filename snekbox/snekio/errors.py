class ParsingError(ValueError):
    """Raised when an incoming content cannot be parsed."""


class IllegalPathError(ParsingError):
    """Raised when a request file has an illegal path."""
