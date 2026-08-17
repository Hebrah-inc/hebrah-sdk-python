"""examples/trigger_mock_event.py

Trigger a mock webhook event against the sandbox connection. Useful for
local dev to confirm your webhook receiver is wired up end-to-end.

Run with:
    HEBRAH_API_KEY=hb_test_... \
    HEBRAH_CONNECTION_ID=conn-sa-... \
    python examples/trigger_mock_event.py [event]

Default event: patient.admitted
"""

from __future__ import annotations

import os
import sys

from hebrah import HebrahClient


def main() -> None:
    api_key = os.environ.get("HEBRAH_API_KEY")
    if not api_key:
        print("HEBRAH_API_KEY is required", file=sys.stderr)
        sys.exit(1)

    connection_id = os.environ.get("HEBRAH_CONNECTION_ID")
    if not connection_id:
        print(
            "HEBRAH_CONNECTION_ID is required for trigger_mock_event",
            file=sys.stderr,
        )
        sys.exit(1)

    event = sys.argv[1] if len(sys.argv) > 1 else "patient.admitted"

    with HebrahClient(
        api_key=api_key,
        base_url=os.environ.get("HEBRAH_API_BASE_URL"),
    ) as client:
        resp = client.webhooks.trigger_mock_event(
            event=event,
            connection_id=connection_id,
        )

    print(
        f"triggered: {resp['event']} "
        f"delivery_id: {resp['delivery_id']} "
        f"status: {resp['status']}"
    )


if __name__ == "__main__":
    main()