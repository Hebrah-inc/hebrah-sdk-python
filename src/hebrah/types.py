from __future__ import annotations

import os
from typing import Any, TypedDict
from urllib.parse import quote, urlparse

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
    params: list[Any]


class DbQueryResponse(TypedDict):
    rows: list[dict[str, Any]]
    row_count: int
    bytes_egressed: int
    duration_ms: float | int
    sql_executed: str


class DbColumnSchema(TypedDict, total=False):
    name: str
    type: str
    nullable: bool
    primary_key: bool
    description: str


class DbTableSchema(TypedDict, total=False):
    table: str
    name: str
    row_count: int
    columns: list[DbColumnSchema]


class DbSchemaResponse(TypedDict, total=False):
    environment_id: str
    addon: str
    tables: list[DbTableSchema]


class EhrSummaryResponse(TypedDict, total=False):
    environment_id: str
    clinic_type: str
    patient_cohort: str
    patient_count: int
    bed_count: int
    occupied_beds: int
    active_encounters: int
    recent_alerts: list[dict[str, Any]]


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


class ConnectionTargetSummary(TypedDict, total=False):
    id: str
    name: str
    pack_id: str
    pack_name: str
    driver: str
    mode: str
    description: str
    available_scopes: list[str]
    tables: list[str]
    incubating: bool


class ConnectionTargetsResponse(TypedDict, total=False):
    targets: list[ConnectionTargetSummary]
    total: int


class ScopedConnection(TypedDict, total=False):
    connection_id: str
    id: str
    org_id: str
    target: str
    driver: str
    mode: str
    scopes: list[str]
    status: str
    purpose: str | None
    agent_id: str | None
    relay_id: str | None
    created_at: str
    revoked_at: str | None


class ConnectionListResponse(TypedDict, total=False):
    connections: list[ScopedConnection]
    total: int


class ExecuteOperationResponse(TypedDict, total=False):
    connection_id: str
    operation: str
    rows: list[dict[str, Any]]
    row_count: int
    result: Any
    audit_event_hash: str
    duration_ms: float | int


class AuditVerifyResponse(TypedDict, total=False):
    connection_id: str
    verified: bool
    valid: bool
    event_count: int
    head_hash: str | None
    broken_at_index: int | None


class RevokeConnectionResponse(TypedDict, total=False):
    connection_id: str
    status: str
    revoked: bool
    revoked_at: str


class AgentWalletSummary(TypedDict, total=False):
    org_id: str
    balance_cents: int
    balance_usd: str
    currency: str
    free_queries_remaining: int
    free_egress_bytes_remaining: int
    auto_reload_enabled: bool
    status: str


class AgentUsageSummary(TypedDict, total=False):
    org_id: str
    queries_run: int
    bytes_egressed: int
    active_environments: int
    active_connections: int
    total_cost_cents: int


class AgentLedgerEntry(TypedDict, total=False):
    id: str
    entry_type: str
    amount_cents: int
    balance_after_cents: int
    description: str
    created_at: str


class AgentLedgerResponse(TypedDict, total=False):
    entries: list[AgentLedgerEntry]
    total: int


LOCAL_HTTP_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]", "::1"})


def safe_path_segment(value: str, name: str = "id") -> str:
    """Validate and URL-encode a single path segment, rejecting empty or traversal segments."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    trimmed = value.strip()
    if trimmed in (".", ".."):
        raise ValueError(f"{name} must not contain path-traversal sequences")
    if "\r" in trimmed or "\n" in trimmed or "\x00" in trimmed:
        raise ValueError(f"{name} contains invalid control characters")
    return quote(trimmed, safe="")


def assert_safe_token(token: str | None, name: str = "api_key") -> str:
    """Validate that a bearer token / API key is non-empty and free of HTTP header control chars."""
    if not token or not isinstance(token, str) or not token.strip():
        raise ValueError(f"{name} is required")
    trimmed = token.strip()
    if "\r" in trimmed or "\n" in trimmed or "\x00" in trimmed:
        raise ValueError(f"{name} contains invalid control characters")
    return trimmed


def assert_safe_base_url(url: str) -> None:
    if not url or not isinstance(url, str) or not url.strip():
        raise ValueError("Invalid base_url: empty URL")
    parsed = urlparse(url.strip())
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
    raw = base_url or os.environ.get("HEBRAH_API_BASE_URL") or DEFAULT_BASE_URL
    url = raw.strip().rstrip("/")
    assert_safe_base_url(url)
    return url
