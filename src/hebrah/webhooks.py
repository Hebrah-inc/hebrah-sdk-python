"""HMAC-SHA256 verification for incoming hebrah webhooks (X-Hebrah-Signature)."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import time
from datetime import datetime

from .errors import WebhookSignatureError
from .types import WebhookEventEnvelope

DEFAULT_TOLERANCE_SECONDS = 300
MAX_TOLERANCE_SECONDS = 86_400
MAX_SIGNATURE_HEADER_LENGTH = 512
_HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def verify_webhook_signature(
    raw_body: str | bytes,
    signature_header: str | bytes | None,
    webhook_secret: str | bytes,
    *,
    max_age_seconds: float | None = None,
    now_timestamp: float | None = None,
    timestamp_header: str | int | float | None = None,
    tolerance_seconds: int | float | None = None,
    require_timestamp: bool = False,
) -> WebhookEventEnvelope:
    """Verify ``X-Hebrah-Signature`` (HMAC-SHA256 hex) and return the parsed payload.

    Raises :class:`WebhookSignatureError` (a subclass of :class:`ValueError`) on invalid
    signatures, malformed JSON, or expired timestamps.
    """
    if (
        not webhook_secret
        or not isinstance(webhook_secret, (str, bytes))
        or (isinstance(webhook_secret, str) and not webhook_secret.strip())
    ):
        raise WebhookSignatureError("webhook_secret is required")

    if signature_header is None:
        raise WebhookSignatureError("Missing X-Hebrah-Signature header")

    try:
        sig_str = (
            signature_header.decode("utf-8")
            if isinstance(signature_header, bytes)
            else str(signature_header)
        ).strip()
    except UnicodeDecodeError as exc:
        raise WebhookSignatureError("Invalid webhook signature") from exc

    if not sig_str:
        raise WebhookSignatureError("Missing X-Hebrah-Signature header")

    if len(sig_str) > MAX_SIGNATURE_HEADER_LENGTH:
        raise WebhookSignatureError("Invalid webhook signature")

    normalized_sig = sig_str[7:].strip() if sig_str.lower().startswith("sha256=") else sig_str
    normalized_sig = normalized_sig.lower()

    if not _HEX_DIGEST_RE.match(normalized_sig):
        raise WebhookSignatureError("Invalid webhook signature")

    effective_tolerance = (
        tolerance_seconds if tolerance_seconds is not None else max_age_seconds
    )
    if effective_tolerance is not None:
        if (
            isinstance(effective_tolerance, bool)
            or not isinstance(effective_tolerance, (int, float))
            or not math.isfinite(effective_tolerance)
            or effective_tolerance < 0
            or effective_tolerance > MAX_TOLERANCE_SECONDS
        ):
            raise WebhookSignatureError(
                f"Webhook replay tolerance must be between 0 and {MAX_TOLERANCE_SECONDS} seconds"
            )

    raw_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    secret_bytes = (
        webhook_secret.encode("utf-8") if isinstance(webhook_secret, str) else webhook_secret
    )

    expected = hmac.new(secret_bytes, raw_bytes, hashlib.sha256).hexdigest()

    if len(normalized_sig) != len(expected) or not hmac.compare_digest(
        expected.lower(), normalized_sig
    ):
        raise WebhookSignatureError("Invalid webhook signature")

    try:
        parsed = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebhookSignatureError("Invalid webhook payload JSON") from exc

    if not isinstance(parsed, dict):
        raise WebhookSignatureError("Invalid webhook payload JSON")

    now_ts = now_timestamp if now_timestamp is not None else time.time()

    if timestamp_header is not None:
        if isinstance(timestamp_header, bool):
            raise WebhookSignatureError("Invalid webhook timestamp")
        try:
            header_ts = float(timestamp_header)
        except (TypeError, ValueError) as exc:
            raise WebhookSignatureError("Invalid webhook timestamp") from exc
        if not math.isfinite(header_ts):
            raise WebhookSignatureError("Invalid webhook timestamp")
        win = (
            float(effective_tolerance)
            if effective_tolerance is not None
            else float(DEFAULT_TOLERANCE_SECONDS)
        )
        if abs(now_ts - header_ts) > win:
            raise WebhookSignatureError("Webhook timestamp outside allowed replay window")
    elif require_timestamp or (effective_tolerance is not None and effective_tolerance > 0):
        raw_ts = parsed.get("timestamp")
        if raw_ts is None:
            raise WebhookSignatureError(
                "Webhook payload missing timestamp required for replay protection"
            )
        if isinstance(raw_ts, bool):
            raise WebhookSignatureError("Invalid webhook timestamp")
        if isinstance(raw_ts, (int, float)):
            if not math.isfinite(raw_ts):
                raise WebhookSignatureError("Invalid webhook timestamp")
            event_ts = float(raw_ts)
        elif isinstance(raw_ts, str):
            try:
                iso = raw_ts.replace("Z", "+00:00") if raw_ts.endswith("Z") else raw_ts
                event_ts = datetime.fromisoformat(iso).timestamp()
            except ValueError as exc:
                raise WebhookSignatureError("Invalid webhook timestamp") from exc
        else:
            raise WebhookSignatureError("Invalid webhook timestamp")

        win = (
            float(effective_tolerance)
            if effective_tolerance is not None
            else float(DEFAULT_TOLERANCE_SECONDS)
        )
        if abs(now_ts - event_ts) > win:
            raise WebhookSignatureError("Webhook timestamp outside allowed replay window")

    return parsed  # type: ignore[return-value]


def assert_webhook_signature(
    raw_body: str | bytes,
    signature_header: str | bytes | None,
    signing_secret: str | bytes,
    *,
    timestamp_header: str | int | float | None = None,
    tolerance_seconds: int | float | None = None,
    require_timestamp: bool = False,
) -> WebhookEventEnvelope:
    """Verify the signature and return the parsed payload."""
    return verify_webhook_signature(
        raw_body,
        signature_header,
        signing_secret,
        timestamp_header=timestamp_header,
        tolerance_seconds=tolerance_seconds,
        require_timestamp=require_timestamp,
    )