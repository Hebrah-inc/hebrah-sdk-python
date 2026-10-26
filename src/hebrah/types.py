"""Typed response models and security helpers for the hebrah Python SDK."""

from __future__ import annotations

import ipaddress
import math
import os
import re
from collections.abc import Sequence
from typing import Any, Literal, TypedDict
from urllib.parse import quote, unquote, urlparse

DEFAULT_BASE_URL = "https://api.hebrah.com"
DEFAULT_MCP_URL = "https://mcp.hebrah.com"
DEFAULT_TIMEOUT_SECONDS = 30.0
MIN_TIMEOUT_SECONDS = 0.1
MAX_TIMEOUT_SECONDS = 300.0
MAX_SQL_LENGTH = 100_000
MAX_SQL_PARAMS = 100
MAX_SQL_PARAM_STRING_LENGTH = 65_536

AccessMode = Literal["read_only", "read_write"]
CustodyModel = Literal["cloud_vault", "customer_relay", "demo_backend"]
EnvironmentStatus = Literal[
    "provisioning",
    "running",
    "paused",
    "paused_insufficient_funds",
    "destroyed",
    "error",
]
EnvironmentModuleType = Literal["postgresql", "sqlite", "vector", "graph"]
ClinicalArchetypeId = Literal[
    "ambulatory_clinic",
    "hospital_system",
    "cardiology_center",
    "emergency_trauma",
    "icu_critical_care",
    "oncology_infusion",
    "orthopedic_surgery",
    "labor_delivery_obgyn",
    "pediatrics_neonatal",
    "behavioral_health",
    "neurology_stroke",
    "nephrology_dialysis",
    "gastroenterology_endoscopy",
    "pulmonology_sleep",
    "rehabilitation_snf",
    "urgent_care_network",
]
ConsultArchitectScopeDecision = Literal[
    "in_scope",
    "adjacent_redirect",
    "out_of_scope_refusal",
]


# ── Isolated Health Environments & Database Modules ───────────


class EnvironmentModuleRecord(TypedDict, total=False):
    id: str
    module_type: str
    status: str
    connection_id: str | None
    config: dict[str, Any]
    created_at: str | None


class EnvironmentRecord(TypedDict, total=False):
    id: str
    organization_id: str
    name: str
    archetype: str
    status: EnvironmentStatus
    region: str
    ttl_hours: int | None
    modules: list[EnvironmentModuleRecord]
    endpoints: dict[str, str]
    patient_count: int
    hourly_rate_cents: int
    expires_at: str | None
    created_at: str | None
    updated_at: str | None


class CreateEnvironmentRequest(TypedDict, total=False):
    name: str
    archetype: str
    modules: list[str]
    patient_count: int
    ttl_hours: int
    seed: int | None
    custom_blueprint: dict[str, Any] | None


class EnvironmentClinicPatient(TypedDict, total=False):
    id: str
    mrn: str
    first_name: str
    last_name: str
    dob: str
    gender: str
    department: str | None
    acuity: str | None
    status: str | None
    conditions: list[str]
    medications: list[str]
    encounters: list[dict[str, Any]]


class EnvironmentScenarioTriggerResponse(TypedDict, total=False):
    status: str
    scenario_type: str
    environment_id: str
    events_emitted: int
    hl7_messages: list[str]
    details: dict[str, Any]


class WireGuardPeerConfigResponse(TypedDict, total=False):
    peer_id: str
    peer_name: str
    environment_id: str
    client_ip: str
    server_public_key: str
    endpoint: str
    config_file: str
    setup_instructions: list[str]
    created_at: str | None


class DbQueryResponse(TypedDict, total=False):
    rows: list[dict[str, Any]]
    row_count: int
    columns: list[str]
    execution_time_ms: float
    module_type: str
    environment_id: str
    audit_event_hash: str | None


class DbVectorSearchResponse(TypedDict, total=False):
    matches: list[dict[str, Any]]
    collection: str
    count: int
    execution_time_ms: float
    environment_id: str


class DbGraphQueryResponse(TypedDict, total=False):
    records: list[dict[str, Any]]
    summary: dict[str, Any]
    execution_time_ms: float
    environment_id: str


class RecordOutcomeResponse(TypedDict, total=False):
    id: str
    environment_id: str
    outcome_type: str
    status: str
    recorded_at: str


# ── Conversational Architect, Studio & Open Data ──────────────


class ConsultArchitectRequest(TypedDict, total=False):
    prompt: str
    session_id: str | None
    current_blueprint: dict[str, Any] | None


class ConsultArchitectResponse(TypedDict, total=False):
    session_id: str
    reply: str
    scope_decision: ConsultArchitectScopeDecision
    blueprint: dict[str, Any]
    clarifying_questions: list[str]
    recommendations: list[dict[str, Any]]
    suggested_archetype: str | None


class ConsultStudioMessage(TypedDict, total=False):
    role: Literal["user", "assistant", "system"]
    content: str


class ConsultStudioRequest(TypedDict, total=False):
    message: str
    session_id: str | None
    history: list[ConsultStudioMessage]
    apply_changes: bool


class ConsultStudioResponse(TypedDict, total=False):
    session_id: str
    reply: str
    scope_decision: ConsultArchitectScopeDecision
    proposed_actions: list[dict[str, Any]]
    applied_actions: list[dict[str, Any]]
    updated_environment: dict[str, Any] | None


class AdmitPatientsResponse(TypedDict, total=False):
    status: str
    environment_id: str
    admitted_count: int
    total_patients: int
    patients: list[EnvironmentClinicPatient]


class OpenDataDataset(TypedDict, total=False):
    id: str
    name: str
    category: str
    description: str
    license: str
    source_url: str
    record_count: int


class OpenDataCatalogResponse(TypedDict, total=False):
    environment_id: str
    datasets: list[OpenDataDataset]
    packs: list[dict[str, Any]]


class EnvironmentAutosaveState(TypedDict, total=False):
    environment_id: str
    enabled: bool
    state: dict[str, Any]
    updated_at: str | None


class ConnectAgentToEnvironmentResponse(TypedDict, total=False):
    status: str
    environment_id: str
    agent_name: str
    connection_id: str | None
    scoped_handle: str | None
    endpoints: dict[str, str]


# ── Agent Self-Registration & Wallet ──────────────────────────


class AgentRegisterResponse(TypedDict, total=False):
    organization_id: str
    api_key: str
    pat: str
    claim_token: str
    claim_url: str
    wallet_balance_cents: int
    trial_credit_dollars: float
    expires_at: str | None


class AgentWalletStatus(TypedDict, total=False):
    organization_id: str
    balance_cents: int
    balance_dollars: float
    currency: str
    trial_credit_active: bool
    auto_reload_enabled: bool
    paused_environments_count: int
    status: str


class AgentTopupResponse(TypedDict, total=False):
    status: str
    amount_cents: int
    new_balance_cents: int
    checkout_url: str | None
    payment_intent_id: str | None
    resumed_environments: int


# ── Connectors & Connections (Phase 1–12) ─────────────────────


class ConnectorPackSummary(TypedDict):
    id: str
    name: str
    tagline: str
    category: str
    status: str
    target_count: int
    demo_target_count: int


class ConnectorTargetSummary(TypedDict, total=False):
    id: str
    pack_id: str
    name: str
    vendor: str
    driver: str
    description: str
    is_demo: bool
    custody_models: list[str]
    default_scopes: list[str]
    available_tables: list[str]
    clinical_Highlight: str | None
    supports_actions: bool
    supported_scenarios: list[str]


class ConnectionScopeDict(TypedDict, total=False):
    access_mode: AccessMode
    allowed_tables: list[str]
    allowed_columns: dict[str, list[str]]
    denied_columns: list[str]
    max_rows: int
    rate_limit_rpm: int
    require_dlp: bool


class ConnectionRecord(TypedDict, total=False):
    id: str
    organization_id: str
    name: str
    pack_id: str
    target_id: str
    driver: str
    custody_model: CustodyModel
    status: str
    scope: ConnectionScopeDict
    baa_acknowledged: bool
    last_used_at: str | None
    created_at: str | None


class ConnectionQueryResponse(TypedDict, total=False):
    connection_id: str
    target_id: str
    driver: str
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    dlp_redactions: int
    audit_hash: str
    latency_ms: float


class ConnectionActionResponse(TypedDict, total=False):
    connection_id: str
    action_type: str
    status: str
    result: dict[str, Any]
    audit_hash: str


class ConnectionScenarioResponse(TypedDict, total=False):
    connection_id: str
    scenario_type: str
    status: str
    details: dict[str, Any]
    hl7_message: str | None
    audit_hash: str


class Hl7MessageRecord(TypedDict, total=False):
    id: str
    connection_id: str
    message_type: str
    trigger_event: str
    patient_id: str | None
    raw_hl7: str
    parsed_segments: dict[str, Any]
    created_at: str


class AuditChainVerification(TypedDict):
    valid: bool
    checked_events: int
    head_hash: str | None
    broken_at_id: str | None


class AgentAccountUsage(TypedDict, total=False):
    organization_id: str
    tier: str
    queries_used: int
    queries_limit: int
    egress_bytes_used: int
    egress_bytes_limit: int
    connections_count: int
    connections_limit: int
    balance_cents: int


# ── Legacy & Clinical Sandbox Models ──────────────────────────


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


class DbQueryParams(TypedDict, total=False):
    sql: str
    addon: str
    actor_type: str
    environment_id: str
    params: list[Any]


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


class WireguardConfigResponse(TypedDict, total=False):
    filename: str
    client_ip: str
    config: str
    instructions: str


class TriggerClinicScenarioResponse(TypedDict, total=False):
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


class SandboxMetrics(TypedDict):
    active_Connections: int
    fhir_Calls_Today: str
    hl7_Events_Emitted: str
    avg_Latency: str


class SandboxPatient(TypedDict):
    id: str
    name: str
    dob: str
    mrn: str
    condition: str
    last_Encounter: str
    fhir_Json: str


class SandboxConfig(TypedDict, total=False):
    ehr_Profile: str
    fhir_Version: str
    patient_Cohort: str
    hl7_Simulation: bool
    strict_Auth: bool
    latency_Injection: str
    error_Rate: str
    custom_Model: dict[str, Any] | None


class WebhookEndpoint(TypedDict):
    id: int
    url: str
    events: str
    status: str


class RegisterWebhookResponse(TypedDict):
    status: str
    endpoint: WebhookEndpoint
    signing_secret: str


class TriggerMockEventResponse(TypedDict, total=False):
    status: str
    event: str
    patient: str
    patient_id: str
    connection_id: str
    envelope_preview: dict[str, Any]
    scenario_id: str
    dispatched_to: int


class WebhookEventEnvelope(TypedDict, total=False):
    id: str
    event: str
    resource: dict[str, Any]
    connection_id: str
    environment: str
    environment_id: str
    timestamp: str | int | float
    org_id: str
    method: str
    path: str
    status_code: int
    latency_ms: int
    data: dict[str, Any]


class SmartTokenResponse(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    patient: str | None


# ── Security & Validation Helpers ─────────────────────────────

_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
_ENCODED_TRAVERSAL_OR_SEP_RE = re.compile(r"%(?:2e|2f|5c|00)", re.IGNORECASE)
_OCTAL_OR_HEX_IPV4_PART_RE = re.compile(r"^(?:0x[0-9a-f]+|0[0-7]+)$", re.IGNORECASE)

_QUICK_SECRET_CHECK_RE = re.compile(
    r"hb_|enc:v[12]:|PrivateKey|Bearer\s|[sr]k_(?:live|test)_|whsec_|eyJ|(?:postgres|redis)",
    re.IGNORECASE,
)

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"hb_(?:live|test|pat|conn|claim|onb)_[A-Za-z0-9_\-]+"), "[REDACTED_HEBRAH_TOKEN]"),
    (re.compile(r"enc:v[12]:[A-Za-z0-9+/=_\-:]+"), "[REDACTED_CIPHERTEXT]"),
    (re.compile(r"(PrivateKey\s*=\s*)[^\s\n\r]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-+/=]+", re.IGNORECASE), r"\1[REDACTED]"),
    (
        re.compile(r"\b(?:[sr]k_(?:live|test)_[A-Za-z0-9]{10,}|whsec_[A-Za-z0-9_\-]{10,})\b"),
        "[REDACTED_SECRET]",
    ),
    (
        re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
        "[REDACTED_JWT]",
    ),
    (
        re.compile(r"\b(?:postgres(?:ql)?|redis(?:s)?):\/\/[^\s\"'<>]+", re.IGNORECASE),
        "[REDACTED_URI]",
    ),
)


def redact_secrets(text: str) -> str:
    """Scrub Hebrah API keys, PATs, claim tokens, Stripe keys, JWTs, DB URIs, and WireGuard keys."""
    if not text or not _QUICK_SECRET_CHECK_RE.search(text):
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def safe_path_segment(value: str, field_name: str = "id") -> str:
    """Validate and URL-encode a single URL path segment to prevent path traversal & smuggling."""
    if not value or not isinstance(value, str):
        raise ValueError(f"{field_name} is required and must be a non-empty string")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{field_name} contains invalid control characters")
    trimmed = value.strip()
    if not trimmed or len(trimmed) > 256:
        raise ValueError(f"{field_name} is required and must be between 1 and 256 characters")
    if "%00" in trimmed.lower():
        raise ValueError(f"{field_name} contains invalid control characters")
    if _ENCODED_TRAVERSAL_OR_SEP_RE.search(trimmed):
        raise ValueError(f"{field_name} contains invalid path-traversal characters")
    decoded = unquote(trimmed)
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in decoded):
        raise ValueError(f"{field_name} contains invalid control characters")
    if (
        trimmed in (".", "..")
        or decoded in (".", "..")
        or ".." in trimmed
        or ".." in decoded
        or "\\" in trimmed
        or "\\" in decoded
        or "?" in trimmed
        or "#" in trimmed
        or "?" in decoded
        or "#" in decoded
    ):
        raise ValueError(f"{field_name} contains invalid path-traversal characters")
    return quote(trimmed, safe="")


def assert_safe_token(value: str | None, field_name: str) -> str:
    """Validate an API key or PAT against empty values, whitespace, and HTTP header injection."""
    if not value or not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} is required (pass {field_name} or set environment variable)"
        )
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{field_name} contains invalid control characters")
    trimmed = value.strip()
    if any(ch.isspace() for ch in trimmed):
        raise ValueError(f"{field_name} contains invalid control characters or whitespace")
    return trimmed


def validate_timeout(
    timeout: float | int | None,
    default: float = DEFAULT_TIMEOUT_SECONDS,
) -> float:
    """Validate HTTP request timeout is a finite number within [0.1, 300.0] seconds."""
    if timeout is None:
        return default
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("timeout must be a finite number between 0.1 and 300.0 seconds")
    val = float(timeout)
    if not math.isfinite(val) or val < MIN_TIMEOUT_SECONDS or val > MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout must be between 0.1 and 300.0 seconds")
    return val


def _is_unsafe_ip(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    allow_localhost: bool = False,
) -> bool:
    if isinstance(addr, ipaddress.IPv6Address):
        # Always reject IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1, ::ffff:169.254.169.254)
        if addr.ipv4_mapped is not None:
            return True
        # Check deprecated IPv4-compatible IPv6 addresses (::w.x.y.z)
        raw_int = int(addr)
        if 0 < raw_int <= 0xFFFFFFFF and raw_int != 1:
            return True
    if allow_localhost and addr.is_loopback:
        return False
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    ):
        return True
    if isinstance(addr, ipaddress.IPv4Address):
        if addr in _CGNAT_NETWORK or addr.packed[0] == 0:
            return True
    return False


def _is_private_or_metadata_host(hostname: str, *, allow_localhost: bool = False) -> bool:
    raw = hostname.strip().lstrip("[").rstrip("]").lower()
    if not raw:
        return True
    # Block DNS trailing-dot bypasses (e.g. localhost., metadata.google.internal.)
    if raw.endswith("."):
        return True
    host = raw
    if allow_localhost and host in ("localhost", "127.0.0.1", "::1"):
        return False
    if (
        host in ("localhost", "metadata.google.internal", "metadata", "instance-data")
        or host.endswith(".localhost")
        or host.endswith(".internal")
    ):
        return True
    if host.endswith(".local"):
        return not allow_localhost

    # Reject integer, hex, or octal IPv4 encodings (e.g. 2130706433, 0x7f000001, 0177.0.0.1)
    if host.isdigit() or host.startswith("0x"):
        return True
    parts = host.split(".")
    if len(parts) <= 4 and all(
        part.isdigit() or bool(_OCTAL_OR_HEX_IPV4_PART_RE.match(part)) for part in parts
    ):
        if len(parts) != 4 or any(
            bool(_OCTAL_OR_HEX_IPV4_PART_RE.match(part)) and part != "0" for part in parts
        ):
            return True

    # Strip IPv6 zone index if present (e.g. fe80::1%lo0)
    ip_candidate = host.split("%", 1)[0]
    try:
        addr = ipaddress.ip_address(ip_candidate)
    except ValueError:
        return False
    return _is_unsafe_ip(addr, allow_localhost=allow_localhost)


def assert_safe_base_url(url: str) -> None:
    """Validate that a base URL uses https:// (or http://localhost) and is SSRF-safe."""
    if not url or not isinstance(url, str) or not url.strip():
        raise ValueError("Invalid base_url: empty URL")
    candidate = url.strip()
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in candidate):
        raise ValueError(f"Invalid base_url: {redact_secrets(candidate)!r}")
    parsed = urlparse(candidate)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError(f"Invalid base_url: {redact_secrets(candidate)!r}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("base_url must not contain embedded credentials")

    raw_hostname = (parsed.hostname or "").lower()
    is_localhost = raw_hostname in ("localhost", "127.0.0.1", "::1")

    if _is_private_or_metadata_host(raw_hostname, allow_localhost=True):
        raise ValueError("base_url cannot target private, link-local, or cloud metadata hosts")

    if not is_localhost and parsed.scheme != "https":
        raise ValueError("base_url must use https:// unless targeting localhost")


def resolve_base_url(base_url: str | None = None) -> str:
    """Resolve and validate the base URL against SSRF and insecure transport."""
    env_url = os.environ.get("HEBRAH_API_BASE_URL") or os.environ.get("HEBRAH_BASE_URL")
    candidate = (
        base_url if base_url is not None else env_url or DEFAULT_BASE_URL
    ).strip()
    assert_safe_base_url(candidate)
    return candidate.rstrip("/")


def assert_safe_external_url(raw_url: str, field_name: str = "url") -> str:
    """Validate an external URL (e.g. webhook or doc_url) against SSRF and non-HTTPS schemes."""
    if not raw_url or not isinstance(raw_url, str) or not raw_url.strip():
        raise ValueError(f"{field_name} must be a non-empty URL string")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in raw_url):
        raise ValueError(f"{field_name} contains invalid control characters")
    trimmed = raw_url.strip()
    parsed = urlparse(trimmed)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid https:// URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{field_name} must not contain embedded credentials")
    hostname = parsed.hostname or ""
    if _is_private_or_metadata_host(hostname, allow_localhost=False):
        raise ValueError(f"{field_name} cannot target private, loopback, or metadata hosts")
    if parsed.scheme != "https":
        raise ValueError(f"{field_name} must use https://")
    return trimmed


def _format_sql_value(val: Any) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        if not math.isfinite(val):
            raise ValueError("SQL parameter numbers must be finite")
        return str(val)
    if isinstance(val, str):
        if "\x00" in val:
            raise ValueError("SQL string parameter cannot contain null bytes")
        if len(val) > MAX_SQL_PARAM_STRING_LENGTH:
            raise ValueError(
                f"SQL string parameter exceeds maximum length of {MAX_SQL_PARAM_STRING_LENGTH}"
            )
        escaped = val.replace("'", "''")
        return f"'{escaped}'"
    raise ValueError(f"Unsupported SQL parameter type: {type(val).__name__}")


_POSITIONAL_PARAM_RE = re.compile(r"\$(\d+)")


def interpolate_sql_params(sql: str, params: Sequence[Any] | None = None) -> str:
    """Safely interpolate positional ($1, $2 or ?) parameters into a read-only SQL query."""
    if not sql or not isinstance(sql, str) or not sql.strip():
        raise ValueError("sql must be a non-empty string")
    if "\x00" in sql:
        raise ValueError("sql cannot contain null bytes")
    if len(sql) > MAX_SQL_LENGTH:
        raise ValueError(f"sql exceeds maximum length of {MAX_SQL_LENGTH} characters")
    if not params:
        return sql
    if len(params) > MAX_SQL_PARAMS:
        raise ValueError(f"Maximum of {MAX_SQL_PARAMS} SQL parameters allowed")

    formatted = [_format_sql_value(p) for p in params]

    if _POSITIONAL_PARAM_RE.search(sql):
        def _replace_positional(match: re.Match[str]) -> str:
            idx = int(match.group(1)) - 1
            if idx < 0 or idx >= len(formatted):
                raise ValueError(
                    f"Missing SQL parameter for placeholder ${match.group(1)}"
                )
            return formatted[idx]

        return _POSITIONAL_PARAM_RE.sub(_replace_positional, sql)

    if "?" in sql:
        q_count = sql.count("?")
        if q_count != len(formatted):
            raise ValueError(
                f"SQL placeholder count ({q_count}) does not match params length ({len(formatted)})"
            )
        parts = sql.split("?")
        out: list[str] = [parts[0]]
        for i, val_str in enumerate(formatted):
            out.append(val_str)
            out.append(parts[i + 1])
        return "".join(out)

    return sql
