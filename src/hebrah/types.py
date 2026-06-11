from __future__ import annotations

import os
from typing import Any, TypedDict

DEFAULT_BASE_URL = "https://api.hebrah.com"


class SandboxCatalog(TypedDict, total=False):
    org_id: str
    org_name: str
    connection_id: str
    environment: str
    sample_patient_ids: list[str]
    supported_events: list[str]
    example_patient_response: dict[str, Any]
    example_webhook_envelope: dict[str, Any]
    ehr_vendor: str | None
    data_format: str | None
    resource_types: list[str] | None
    field_mappings: dict[str, Any] | None


class PatientSummary(TypedDict):
    id: str


class PatientListResponse(TypedDict):
    patients: list[PatientSummary]


class TriggerMockEventResponse(TypedDict, total=False):
    status: str
    event: str
    patient_id: str
    connection_id: str
    envelope_preview: dict[str, Any]


class WebhookEventEnvelope(TypedDict, total=False):
    event: str
    resource: dict[str, Any]
    connection_id: str
    environment: str
    timestamp: str
    org_id: str
    method: str
    path: str
    status_code: int
    latency_ms: int


def resolve_base_url(base_url: str | None = None) -> str:
    url = base_url or os.environ.get("HEBRAH_API_BASE_URL") or DEFAULT_BASE_URL
    return url.rstrip("/")