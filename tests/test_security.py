"""Comprehensive security, performance, and Isolated Health Environments parity tests."""

from __future__ import annotations

import hashlib
import hmac
import pickle
import time

import httpx
import pytest
import respx

from hebrah import (
    HebrahAgentHarness,
    HebrahApiError,
    HebrahClient,
    WebhookSignatureError,
    assert_webhook_signature,
    interpolate_sql_params,
    redact_secrets,
    validate_timeout,
    verify_webhook_signature,
)
from hebrah.types import (
    assert_safe_external_url,
    assert_safe_token,
    resolve_base_url,
    safe_path_segment,
)

# ── SDK-PY-01: SSRF Protection (IPv4, IPv6, CGNAT, Octal/Hex, Metadata) ──


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "https://169.254.169.254/latest/meta-data/",
        "https://[::ffff:169.254.169.254]/latest/meta-data/",
        "https://[::ffff:a9fe:a9fe]/latest/meta-data/",
        "https://[::ffff:127.0.0.1]/admin",
        "https://[::ffff:10.0.0.1]/internal",
        "https://[::169.254.169.254]/legacy-v4-compat",
        "https://[::]/unspecified",
        "https://[ff02::1]/multicast",
        "https://[fe80::1]/link-local",
        "https://[fd00::1234]/ula-private",
        "https://100.100.100.200/latest/meta-data/",
        "https://100.64.0.1/cgnat",
        "https://0.0.0.0/zero",
        "https://255.255.255.255/broadcast",
        "https://2130706433/decimal-loopback",
        "https://0x7f000001/hex-loopback",
        "https://0177.0.0.1/octal-loopback",
        "https://localhost./trailing-dot",
        "https://sub.localhost/subdomain-localhost",
        "https://metadata.google.internal./computeMetadata/v1/",
        "https://service.internal./api",
        "https://printer.local./ipp",
    ],
)
def test_ssrf_blocks_advanced_ip_and_hostname_bypasses(unsafe_url: str) -> None:
    with pytest.raises(ValueError, match="private|loopback|metadata|link-local"):
        assert_safe_external_url(unsafe_url, "webhook_url")

    with pytest.raises(ValueError, match="private|link-local|metadata"):
        resolve_base_url(unsafe_url)


def test_ssrf_blocks_embedded_credentials_and_cleartext_http() -> None:
    with pytest.raises(ValueError, match="embedded credentials"):
        assert_safe_external_url("https://admin:secret@hooks.example.com/webhook")

    with pytest.raises(ValueError, match="embedded credentials"):
        resolve_base_url("https://admin:secret@api.hebrah.com")

    with pytest.raises(ValueError, match="must use https://"):
        assert_safe_external_url("http://hooks.example.com/webhook")


# ── SDK-PY-02: Path Traversal & Encoded Smuggling Prevention ───────────


@pytest.mark.parametrize(
    "malicious_segment",
    [
        "",
        "   ",
        ".",
        "..",
        "../admin",
        "env_1/../../secret",
        "%2e%2e",
        "%2E%2E%2Fadmin",
        "env%2f..%2fsecret",
        "env%5cadmin",
        "env\\admin",
        "env?admin=true",
        "env#fragment",
        "env\x00null",
        "env%00null",
        "env\r\nheader",
        "a" * 257,
    ],
)
def test_safe_path_segment_rejects_traversal_and_smuggling(malicious_segment: str) -> None:
    with pytest.raises(ValueError):
        safe_path_segment(malicious_segment, "environment_id")


def test_safe_path_segment_allows_valid_ids() -> None:
    assert safe_path_segment("env_abc-123", "environment_id") == "env_abc-123"
    assert safe_path_segment("  patient_42  ", "patient_id") == "patient_42"


# ── SDK-PY-03: Token & Timeout Validation ──────────────────────────────


@pytest.mark.parametrize(
    "bad_token",
    [
        "",
        "   ",
        "hb_live_abc\r\nX-Injected: 1",
        "hb_live_abc\n",
        "\thb_live_abc",
        "hb_live_abc\x00def",
        "hb_live_abc def",
    ],
)
def test_assert_safe_token_rejects_control_chars_and_whitespace(bad_token: str) -> None:
    with pytest.raises(ValueError):
        assert_safe_token(bad_token, "api_key")


@pytest.mark.parametrize("bad_timeout", [0, -5, 0.05, 301.0, float("inf"), float("nan"), True])
def test_validate_timeout_rejects_out_of_range_values(bad_timeout: object) -> None:
    with pytest.raises(ValueError, match="timeout"):
        validate_timeout(bad_timeout)  # type: ignore[arg-type]


def test_validate_timeout_accepts_valid_values() -> None:
    assert validate_timeout(None) == 30.0
    assert validate_timeout(15) == 15.0
    assert validate_timeout(0.5) == 0.5


# ── SDK-PY-04: Secret Redaction, Error Truncation & Pickle Safety ──────


def test_redact_secrets_scrubs_all_credential_formats() -> None:
    fake_stripe = "_".join(["sk", "live", "1234567890abcdefghijklmn"])
    fake_whsec = "_".join(["whsec", "1234567890abcdefghijklmn"])
    fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJlMTIzNDU2"
    raw = (
        f"Keys: hb_live_abc123XYZ hb_claim_tok999 enc:v1:YWJjZGVm "
        f"PrivateKey = aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5zA7bC9d= "
        f"Authorization: Bearer secret_jwt_token "
        f"Stripe: {fake_stripe} Webhook: {fake_whsec} JWT: {fake_jwt} "
        f"DB: postgresql://admin:supersecret@10.0.0.5:5432/hebrah "
        f"Redis: rediss://default:redispass@10.0.0.6:6379/0"
    )
    scrubbed = redact_secrets(raw)
    assert "hb_live_abc123XYZ" not in scrubbed
    assert "hb_claim_tok999" not in scrubbed
    assert "YWJjZGVm" not in scrubbed
    assert "aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5zA7bC9d=" not in scrubbed
    assert "secret_jwt_token" not in scrubbed
    assert fake_stripe not in scrubbed
    assert fake_whsec not in scrubbed
    assert fake_jwt not in scrubbed
    assert "supersecret" not in scrubbed
    assert "redispass" not in scrubbed
    assert "[REDACTED]" in scrubbed
    assert "[REDACTED_SECRET]" in scrubbed
    assert "[REDACTED_JWT]" in scrubbed
    assert "[REDACTED_URI]" in scrubbed


def test_hebrah_api_error_truncates_oversized_detail_and_redacts() -> None:
    huge_detail = "hb_live_secret999 " + ("X" * 10_000)
    err = HebrahApiError("Failed with Bearer my_secret_tok", 500, huge_detail)
    assert "my_secret_tok" not in err.message
    assert "hb_live_secret999" not in (err.detail or "")
    assert err.detail is not None
    assert len(err.detail) <= 4096 + len("...[truncated]")
    assert err.detail.endswith("...[truncated]")
    serialized = err.to_dict()
    assert serialized["status"] == 500
    assert "hb_live_secret999" not in str(serialized)


def test_pickle_does_not_leak_client_or_harness_credentials() -> None:
    client = HebrahClient(api_key="hb_live_top_secret_key", base_url="https://api.hebrah.com")
    harness = HebrahAgentHarness(pat="hb_pat_top_secret_pat", mcp_url="https://mcp.hebrah.com/mcp")
    try:
        client_bytes = pickle.dumps(client)
        harness_bytes = pickle.dumps(harness)
        assert b"hb_live_top_secret_key" not in client_bytes
        assert b"hb_pat_top_secret_pat" not in harness_bytes
    finally:
        client.close()
        harness.close()


# ── SDK-PY-05: SQL Parameter Interpolation Safety ──────────────────────


def test_interpolate_sql_params_positional_and_question_marks() -> None:
    sql1 = interpolate_sql_params(
        "SELECT * FROM patients WHERE department = $1 AND acuity <= $2 "
        "AND active = $3 AND deleted_at IS $4",
        ["Cardiology", 3, True, None],
    )
    expected = (
        "SELECT * FROM patients WHERE department = 'Cardiology' AND acuity <= 3 "
        "AND active = TRUE AND deleted_at IS NULL"
    )
    assert sql1 == expected

    sql2 = interpolate_sql_params(
        "SELECT * FROM patients WHERE last_name = ?",
        ["O'Connor'; DROP TABLE patients; --"],
    )
    assert sql2 == "SELECT * FROM patients WHERE last_name = 'O''Connor''; DROP TABLE patients; --'"


def test_interpolate_sql_params_rejects_unsafe_inputs() -> None:
    with pytest.raises(ValueError, match="null bytes"):
        interpolate_sql_params("SELECT * FROM patients WHERE id = $1", ["pat\x00123"])

    with pytest.raises(ValueError, match="finite"):
        interpolate_sql_params("SELECT * FROM patients WHERE score > $1", [float("nan")])

    with pytest.raises(ValueError, match="Missing SQL parameter"):
        interpolate_sql_params("SELECT * FROM patients WHERE id = $2", ["only-one"])


# ── SDK-PY-06: Webhook Signature Hardening ─────────────────────────────


def test_webhook_rejects_excessive_tolerance_and_malformed_hex() -> None:
    body = '{"event":"ADT^A01"}'
    secret = "wh_secret_key"
    digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    # Tolerance > 86400s rejected
    with pytest.raises(WebhookSignatureError, match="between 0 and 86400"):
        verify_webhook_signature(
            body,
            f"sha256={digest}",
            secret,
            timestamp_header=int(time.time()),
            tolerance_seconds=100_000,
        )
    # Negative tolerance rejected
    with pytest.raises(WebhookSignatureError, match="between 0 and 86400"):
        verify_webhook_signature(
            body,
            f"sha256={digest}",
            secret,
            tolerance_seconds=-1,
        )
    # Non-hex signature rejected
    with pytest.raises(WebhookSignatureError, match="Invalid webhook signature"):
        verify_webhook_signature(body, "sha256=" + ("z" * 64), secret)
    # Boolean timestamp rejected
    with pytest.raises(WebhookSignatureError, match="Invalid webhook timestamp"):
        verify_webhook_signature(
            body,
            f"sha256={digest}",
            secret,
            timestamp_header=True,  # type: ignore[arg-type]
        )
    with pytest.raises(WebhookSignatureError):
        assert_webhook_signature(body, "sha256=deadbeef", secret)


# ── Isolated Health Environments & Agent Parity Tests ──────────────────


@respx.mock
def test_environments_architect_studio_admit_opendata_autosave_and_topup() -> None:
    respx.post("https://api.hebrah.com/v1/environments/architect").mock(
        return_value=httpx.Response(
            200,
            json={
                "session_id": "arch_1",
                "reply": "Designed Cardiology Center blueprint.",
                "scope_decision": "in_scope",
                "blueprint": {"archetype": "cardiology_center"},
            },
        )
    )
    respx.post("https://api.hebrah.com/v1/environments/env_1/studio/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "session_id": "stud_1",
                "reply": "Added 5 ICU beds.",
                "scope_decision": "in_scope",
            },
        )
    )
    respx.post("https://api.hebrah.com/v1/environments/env_1/ehr/patients/generate").mock(
        return_value=httpx.Response(
            200,
            json={"status": "admitted", "environment_id": "env_1", "admitted_count": 3},
        )
    )
    respx.get("https://api.hebrah.com/v1/environments/env_1/open-data/catalog").mock(
        return_value=httpx.Response(
            200,
            json={"environment_id": "env_1", "datasets": [{"id": "dicom_imaging_v1"}]},
        )
    )
    respx.post("https://api.hebrah.com/v1/environments/env_1/agents/connect").mock(
        return_value=httpx.Response(
            200,
            json={"status": "connected", "environment_id": "env_1", "agent_name": "triage-bot"},
        )
    )
    respx.get("https://api.hebrah.com/v1/environments/env_1/autosave").mock(
        return_value=httpx.Response(
            200,
            json={"environment_id": "env_1", "enabled": True, "state": {"step": 2}},
        )
    )
    respx.put("https://api.hebrah.com/v1/environments/env_1/autosave").mock(
        return_value=httpx.Response(
            200,
            json={"environment_id": "env_1", "enabled": True, "state": {"step": 3}},
        )
    )
    respx.post("https://api.hebrah.com/v1/environments/env_1/db/outcomes").mock(
        return_value=httpx.Response(
            200,
            json={"id": "out_1", "environment_id": "env_1", "outcome_type": "sepsis_detected"},
        )
    )
    respx.post("https://api.hebrah.com/v1/agent/topup").mock(
        return_value=httpx.Response(
            200,
            json={"status": "succeeded", "amount_cents": 2500, "new_balance_cents": 3000},
        )
    )

    with HebrahClient(api_key="hb_test_123", environment_id="env_1") as client:
        arch = client.environments.consult_architect("Need a 50-bed cardiology hospital")
        assert arch["scope_decision"] == "in_scope"

        studio = client.environments.consult_studio("Add 5 ICU beds", apply_changes=True)
        assert studio["session_id"] == "stud_1"

        admitted = client.environments.admit_patients(count=3, department="Cardiology")
        assert admitted["admitted_count"] == 3

        catalog = client.environments.open_data_catalog()
        assert catalog["datasets"][0]["id"] == "dicom_imaging_v1"

        conn = client.environments.connect_agent(agent_name="triage-bot")
        assert conn["status"] == "connected"

        autosave = client.environments.get_autosave()
        assert autosave["state"]["step"] == 2

        updated_as = client.environments.update_autosave({"step": 3})
        assert updated_as["state"]["step"] == 3

        outcome = client.db.record_outcome("sepsis_detected", details={"lactate": 4.2})
        assert outcome["id"] == "out_1"

        topup = client.agent.topup(2500)
        assert topup["new_balance_cents"] == 3000


@respx.mock
def test_harness_handles_sse_and_is_error_and_normalizes_mcp_url() -> None:
    sse_payload = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":1,"result":{"content":'
        '[{"type":"text","text":"{\\"scope_decision\\":\\"in_scope\\"}"}]}}\n\n'
    )
    route = respx.post("https://mcp.hebrah.com/mcp").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=sse_payload,
        )
    )
    with HebrahAgentHarness(pat="hb_pat_123", mcp_url="https://mcp.hebrah.com/mcp") as harness:
        assert harness.mcp_url == "https://mcp.hebrah.com"
        res = harness.consult_architect("Build an emergency trauma center")
        assert res["scope_decision"] == "in_scope"
        assert "text/event-stream" in route.calls[0].request.headers["accept"]

    # Verify isError: True raises HebrahApiError with redacted message
    respx.post("https://mcp.hebrah.com/mcp").mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": "Failed with token hb_pat_secret999"}],
                },
            },
        )
    )
    with HebrahAgentHarness(pat="hb_pat_123", mcp_url="https://mcp.hebrah.com") as harness:
        with pytest.raises(HebrahApiError) as exc_info:
            harness.wallet_status()
        assert "hb_pat_secret999" not in str(exc_info.value)
        assert "[REDACTED_HEBRAH_TOKEN]" in str(exc_info.value)


@respx.mock
def test_register_agent_and_vector_graph_and_harness_helpers() -> None:
    respx.post("https://api.hebrah.com/v1/agent/account").mock(
        return_value=httpx.Response(
            201,
            json={
                "orgId": "org_1",
                "orgName": "py-bot",
                "apiKey": "hb_conn_abc",
                "keyPrefix": "hb_conn_abc",
                "mcpEndpointUrl": "https://mcp.hebrah.com",
                "claimUrl": "https://app.hebrah.com/claim-org/hb_claim_123",
                "trial": {"credits": {"queries": 1000, "egressBytes": 50000000}, "status": "trial"},
            },
        )
    )
    reg = HebrahClient.register_agent(
        agent_name="py-bot",
        owner_email="dev@company.io",
        purpose="Automated QA",
    )
    assert reg["organization_id"] == "org_1"
    assert reg["api_key"] == "hb_conn_abc"

    respx.post("https://api.hebrah.com/v1/environments/env_1/vector/search").mock(
        return_value=httpx.Response(
            200,
            json={"collection": "clinical_notes", "matches": [{"id": "pt_1", "score": 0.95}]},
        )
    )
    respx.post("https://api.hebrah.com/v1/environments/env_1/graph/cypher").mock(
        return_value=httpx.Response(
            200,
            json={"nodes": [{"id": "n1"}], "edges": [], "records": [{"cnt": 5}]},
        )
    )
    respx.get("https://api.hebrah.com/v1/environments/env_1/ehr/patients").mock(
        return_value=httpx.Response(
            200,
            json={"patients": [{"patient_id": "pt_1", "name": "Jane Doe"}]},
        )
    )

    with HebrahClient(api_key="hb_test_123", environment_id="env_1") as client:
        vec = client.db.vector_search("sepsis lactate", top_k=3)
        assert vec["matches"][0]["id"] == "pt_1"

        graph = client.db.graph_query("MATCH (n) RETURN count(n) AS cnt")
        assert graph["records"][0]["cnt"] == 5

        pts = client.environments.list_patients(department="ICU", acuity="critical", limit=10)
        assert pts[0]["patient_id"] == "pt_1"

