from __future__ import annotations

import hashlib
import hmac
import json

from hebrah.types import WebhookEventEnvelope


def verify_webhook_signature(
    raw_body: bytes | str,
    signature_header: str | None,
    webhook_secret: str,
) -> WebhookEventEnvelope:
    """Verify X-Hebrah-Signature (HMAC-SHA256 hex) and return the parsed payload."""
    if not signature_header:
        raise ValueError("Missing X-Hebrah-Signature header")

    raw = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw,
        hashlib.sha256,
    ).hexdigest()

    if len(signature_header) != len(expected):
        raise ValueError("Invalid webhook signature")

    if not hmac.compare_digest(expected, signature_header):
        raise ValueError("Invalid webhook signature")

    return json.loads(raw.decode("utf-8"))