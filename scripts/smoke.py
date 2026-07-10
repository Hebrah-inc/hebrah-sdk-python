#!/usr/bin/env python3
"""Smoke test against a local or staging hebrah-api instance."""

from __future__ import annotations

import os
import sys

from hebrah import HebrahClient


def main() -> None:
    api_key = os.environ.get("HEBRAH_API_KEY")
    if not api_key:
        print(
            "HEBRAH_API_KEY is required (use SEED_API_KEY from scripts/generate-local-secrets.sh)",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = os.environ.get("HEBRAH_API_BASE_URL", "http://localhost:8000")

    with HebrahClient(api_key=api_key, base_url=base_url) as client:
        health = client.health()
        print("health:", health.get("status"))

        catalog = client.sandbox.catalog()
        patient_id = catalog["sample_patient_ids"][0]
        patient = client.sandbox.resource("Patient", patient_id)
        print("patient:", patient.get("resourceType"), patient.get("id"))

    print("smoke ok")


if __name__ == "__main__":
    main()
