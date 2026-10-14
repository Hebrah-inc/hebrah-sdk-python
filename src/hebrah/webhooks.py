from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import json
import re
import time

from hebrah.types import WebhookEventEnvelope

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def verify_webhook_signature(
    raw_body: bytes | str,
    signature_header: str | None,
    webhook_secret: str,
    *,
    max_age_seconds: float | None = None,
    now_timestamp: float | None = None,
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

    if not _HEX64_RE.match(normalized_sig):
        raise ValueError("Invalid webhook signature")

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

    if max_age_seconds is not None and max_age_seconds > 0:
        raw_ts = parsed.get("timestamp")
        if raw_ts is None:
            raise ValueError("Webhook payload missing timestamp required for replay protection")
        if isinstance(raw_ts, (int, float)):
            event_ts = float(raw_ts)
        elif isinstance(raw_ts, str):
            try:
                iso = raw_ts.replace("Z", "+00:00") if raw_ts.endswith("Z") else raw_ts
                event_ts = datetime.fromisoformat(iso).timestamp()
            except ValueError as exc:
                raise ValueError("Invalid webhook timestamp") from exc
        else:
            raise ValueError("Invalid webhook timestamp")
        now_ts = now_timestamp if now_timestamp is not None else time.time()
        if abs(now_ts - event_ts) > max_age_seconds:
            raise ValueError("Webhook timestamp outside allowed replay window")

    return parsed