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
    if not webhook_secret or not isinstance(webhook_secret, str) or not webhook_secret.strip():
        raise ValueError("webhook_secret is required")

    if (
        not signature_header
        or not isinstance(signature_header, str)
        or not signature_header.strip()
    ):
        raise ValueError("Missing X-Hebrah-Signature header")

    normalized_sig = signature_header.strip()
    if normalized_sig.lower().startswith("sha256="):
        normalized_sig = normalized_sig[7:].strip()
    normalized_sig = normalized_sig.lower()

    raw = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw,
        hashlib.sha256,
    ).hexdigest()

    if len(normalized_sig) != len(expected):
        raise ValueError("Invalid webhook signature")

    if not hmac.compare_digest(expected, normalized_sig):
        raise ValueError("Invalid webhook signature")

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid webhook payload JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Invalid webhook payload JSON")

    return parsed