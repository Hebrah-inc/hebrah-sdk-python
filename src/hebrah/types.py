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


class CreateEnvironmentParams(TypedDict, total=False):
    name: str
    clinic_type: str
    patient_cohort: str
    patient_count: int
    bed_count: int
    addons: list[str]


class EnvironmentSummary(TypedDict, total=False):
    id: str
    org_id: str
    name: str
    clinic_type: str
    patient_cohort: str
    status: str
    addons: list[str]
    patient_count: int
    bed_count: int
    endpoints: dict[str, str]
    wireguard_ip: str | None
    queries_run: int
    bytes_egressed: int
    hourly_rate_cents: int
    total_cost_cents: int
    connected_agents_count: int
    last_active_at: str | None
    created_at: str


class EnvironmentDetail(EnvironmentSummary, total=False):
    connection_instructions: dict[str, Any]
    database_modules: list[dict[str, Any]]
    connected_agents: list[dict[str, Any]]


class DbQueryParams(TypedDict, total=False):
    sql: str
    addon: str
    actor_type: str
    environment_id: str


class DbQueryResponse(TypedDict):
    rows: list[dict[str, Any]]
    row_count: int
    bytes_egressed: int
    duration_ms: float | int
    sql_executed: str


class WireguardConfigResponse(TypedDict):
    filename: str
    client_ip: str
    config: str
    instructions: str


class TriggerClinicScenarioResponse(TypedDict):
    success: bool
    scenario: str
    patient_id: str
    hl7_event: str
    broadcasted: bool


class EnvironmentLogItem(TypedDict, total=False):
    id: str
    environment_id: str
    actor_type: str
    actor_id: str
    event_type: str
    summary: str
    details: dict[str, Any]
    duration_ms: float | int | None
    status: str
    created_at: str


LOCAL_HTTP_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})


def assert_safe_base_url(url: str) -> None:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid base_url: {url}")

    if parsed.scheme == "https":
        return

    if parsed.scheme == "http" and parsed.hostname in LOCAL_HTTP_HOSTS:
        return

    raise ValueError(
        "base_url must use https:// or http://localhost/127.0.0.1 for local development "
        f"(got {parsed.scheme}://{parsed.hostname})"
    )


def resolve_base_url(base_url: str | None = None) -> str:
    url = (base_url or os.environ.get("HEBRAH_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    assert_safe_base_url(url)
    return url
