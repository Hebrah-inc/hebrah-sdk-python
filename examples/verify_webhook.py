"""examples/verify_webhook.py

Minimal webhook signature verification using `verify_webhook_signature`.
Drop this into a Flask / FastAPI / Django handler — the request body bytes
and the `X-Hebrah-Signature` header must reach it unmodified.

Run with:
    HEBRAH_WEBHOOK_SECRET=hbsec_... python examples/verify_webhook.py <raw-body> <signature>

NOTE: This example deliberately prints only the event type and delivery
timestamp. `patient_id` and `connection_id` from the envelope are PHI /
internal identifiers and must never be logged. See `SECURITY.md`.
"""

from __future__ import annotations

import os
import sys

from hebrah import HebrahApiError, verify_webhook_signature


def main() -> None:
    secret = os.environ.get("HEBRAH_WEBHOOK_SECRET")
    if not secret:
        print("HEBRAH_WEBHOOK_SECRET is required", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) != 3:
        print(
            "usage: python examples/verify_webhook.py <raw-body> <signature>",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_body, signature = sys.argv[1], sys.argv[2]

    try:
        envelope = verify_webhook_signature(raw_body, signature, secret)
    except HebrahApiError as err:
        print(f"verification failed: {err.message}", file=sys.stderr)
        sys.exit(1)

    print(f"verified event: {envelope['event']} at {envelope['delivered_at']}")


if __name__ == "__main__":
    main()