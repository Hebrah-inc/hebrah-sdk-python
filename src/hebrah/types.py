from __future__ import annotations

import os
from typing import Any, TypedDict

DEFAULT_BASE_URL = "https://api.hebrah.com"


class SandboxScenarioSummary(TypedDict, total=False):
    id: str
    name: str
    description: str
    events: list[str]
    delay_seconds: float | int


class SandboxDomainSummary(TypedDict, total=False):
    id: str
    name: str
    description: str
    events: list[str]
    resource_types: list[str]
    hl7_message_types: dict[str, str]
    scenarios: list[SandboxScenarioSummary]


class SandboxCatalog(TypedDict, total=False):
    org_id: str
    org_name: str
    connection_id: str
    environment: str
    sample_patient_ids: list[str]
    supported_events: list[str]
    example_patient_response: dict[str, Any]
    example_webhook_envelope: dict[str, Any]
    sandbox_domains: list[SandboxDomainSummary]
    event_groups: dict[str, list[str]]
    example_envelopes: dict[str, dict[str, Any]]
    ehr_vendor: str | None
    data_format: str | None
    resource_types: list[str] | None
    field_mappings: list[dict[str, Any]] | None


class SandboxResourceListResponse(TypedDict):
    resource_type: str
    ids: list[str]


class PayerRules(TypedDict):
    id: str
    name: str
    required_documents: list[str]
    typical_pend_reasons: list[str]
    typical_denial_reasons: list[str]


class RunScenarioResponse(TypedDict):
    status: str
    scenario_id: str
    connection_id: str
    events: list[str]
    envelope_previews: list[dict[str, Any]]


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
    scenario_id: str


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
