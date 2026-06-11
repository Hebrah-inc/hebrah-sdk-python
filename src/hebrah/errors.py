class HebrahApiError(Exception):
    """Raised when the control plane returns a non-success HTTP status."""

    def __init__(self, message: str, status: int, detail: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail
