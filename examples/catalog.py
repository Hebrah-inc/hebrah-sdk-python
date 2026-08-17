"""examples/catalog.py

Fetch the sandbox catalog for the active org and print a summary.

Run with:
    HEBRAH_API_KEY=hb_test_... python examples/catalog.py

Optional: HEBRAH_API_BASE_URL=http://localhost:8000
Optional: HEBRAH_CONNECTION_ID=conn-sa-...
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

    with HebrahClient(
        api_key=api_key,
        base_url=os.environ.get("HEBRAH_API_BASE_URL"),
        default_connection_id=os.environ.get("HEBRAH_CONNECTION_ID"),
    ) as client:
        catalog = client.sandbox.catalog()

    print(f"org: {catalog['org_name']} ({catalog['org_id']})")
    print(f"connection: {catalog['connection_id']} {catalog['environment']}")
    print(f"sample patients: {catalog['sample_patient_ids']}")
    print(f"supported events: {catalog['supported_events']}")


if __name__ == "__main__":
    main()