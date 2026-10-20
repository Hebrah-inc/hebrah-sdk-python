"""Exceptions raised by the hebrah Python SDK."""

from __future__ import annotations

from typing import Any

from .types import redact_secrets

MAX_ERROR_DETAIL_LENGTH = 4096


class HebrahApiError(Exception):
    """Non-2xx HTTP response or transport failure from hebrah-api or hebrah-mcp-host."""

    def __init__(
        self,
        message: str,
        status: int,
        detail: str | None = None,
    ) -> None:
        safe_message = redact_secrets(message)
        safe_detail: str | None = None
        if detail is not None:
            scrubbed = redact_secrets(detail)
            if len(scrubbed) > MAX_ERROR_DETAIL_LENGTH:
                safe_detail = f"{scrubbed[:MAX_ERROR_DETAIL_LENGTH]}...[truncated]"
            else:
                safe_detail = scrubbed

        super().__init__(safe_message)
        self.message = safe_message
        self.status = status
        self.detail = safe_detail

    def __str__(self) -> str:
        if self.detail:
            return f"{self.message} [status={self.status}]: {self.detail}"
        return f"{self.message} [status={self.status}]"

    def __repr__(self) -> str:
        return (
            f"HebrahApiError(message={self.message!r}, "
            f"status={self.status!r}, detail={self.detail!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": "HebrahApiError",
            "message": self.message,
            "status": self.status,
            "detail": self.detail,
        }


class WebhookSignatureError(ValueError):
    """Raised when an incoming webhook fails HMAC-SHA256 verification."""
