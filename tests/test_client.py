import hashlib
import hmac
import json

import httpx
import pytest
import respx

from hebrah import (
    HebrahAgentHarness,
    HebrahApiError,
    HebrahClient,
    assert_safe_token,
    resolve_base_url,
    safe_path_segment,
    verify_webhook_signature,
)

BASE = "https://api.test.local"


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("HEBRAH_API_KEY", raising=False)
    with pytest.raises(ValueError, match="api_key is required"):
        HebrahClient(api_key="")


def test_env_var_fallbacks(monkeypatch):
    monkeypatch.setenv("HEBRAH_API_KEY", "hb_env_key")
    monkeypatch.setenv("HEBRAH_ENVIRONMENT_ID", "env-from-os")
    monkeypatch.setenv("HEBRAH_CONNECTION_ID", "conn-from-os")
    with HebrahClient(base_url=BASE) as client:
        assert client._environment_id == "env-from-os"
        assert client._default_connection_id == "conn-from-os"


def test_rejects_control_characters_in_api_key():
    with pytest.raises(ValueError, match="api_key contains invalid control characters"):
        HebrahClient(api_key="hb_test_key\r\nX-Injected: 1", base_url=BASE)


def test_safe_path_segment_blocks_traversal_and_control_chars():
    assert safe_path_segment("env-123") == "env-123"
    assert safe_path_segment("foo/bar") == "foo%2Fbar"
    with pytest.raises(ValueError, match="id is required"):
        safe_path_segment("")
    with pytest.raises(ValueError, match="path-traversal"):
        safe_path_segment("..")
    with pytest.raises(ValueError, match="path-traversal"):
        safe_path_segment(".")
    with pytest.raises(ValueError, match="control characters"):
        safe_path_segment("abc\ndef")


def test_assert_safe_token():
    assert assert_safe_token("  hb_pat_123  ", "pat") == "hb_pat_123"
    with pytest.raises(ValueError, match="pat is required"):
        assert_safe_token("   ", "pat")
    with pytest.raises(ValueError, match="invalid control characters"):
        assert_safe_token("hb_pat_123\x00", "pat")


def test_allows_https_base_url():
    with HebrahClient(api_key="hb_test_key", base_url="https://api.hebrah.com") as client:
        assert client.base_url == "https://api.hebrah.com"


def test_allows_http_localhost_base_url():
    with HebrahClient(api_key="hb_test_key", base_url="http://localhost:8000") as client:
        assert client.base_url == "http://localhost:8000"


def test_rejects_non_local_http_base_url():
    with pytest.raises(ValueError, match="base_url must use https"):
        HebrahClient(api_key="hb_test_key", base_url="http://evil.example.com")


def test_harness_validates_pat_and_urls():
    with pytest.raises(ValueError, match="pat is required"):
        HebrahAgentHarness(pat="")
    with pytest.raises(ValueError, match="base_url must use https"):
        HebrahAgentHarness(pat="hb_pat_123", mcp_url="http://evil.example.com")
    with HebrahAgentHarness(
        pat="hb_pat_123",
        mcp_url="https://mcp.hebrah.com/",
        integration_agent_url="http://localhost:3050/",
        dashboard_url="https://app.hebrah.com/",
    ) as harness:
        assert harness.mcp_url == "https://mcp.hebrah.com"
        assert harness.integration_agent_url == "http://localhost:3050"
        assert harness.dashboard_url == "https://app.hebrah.com"


@respx.mock
def test_sandbox_catalog():
    catalog = {
        "org_id": "org-1",
        "org_name": "Acme",
        "connection_id": "conn-sa-1",
        "environment": "sandbox",
        "sample_patient_ids": ["pat_01"],
        "supported_events": ["patient.admitted"],
        "example_patient_response": {},
        "example_webhook_envelope": {},
    }
    respx.get(f"{BASE}/v1/sandbox/catalog").mock(
        return_value=httpx.Response(200, json=catalog)
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        result = client.sandbox.catalog()

    assert result["org_id"] == "org-1"
    assert respx.calls[0].request.headers["Authorization"] == "Bearer hb_test_key"


@respx.mock
def test_encodes_special_characters_in_sandbox_domain_path():
    respx.get(f"{BASE}/v1/sandbox/domains/foo%2Fbar").mock(
        return_value=httpx.Response(200, json={"id": "foo/bar"})
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        client.sandbox.domain("foo/bar")

    assert respx.calls[0].request.url.raw_path == b"/v1/sandbox/domains/foo%2Fbar"


@respx.mock
def test_get_patient():
    patient = {"resourceType": "Patient", "id": "pat_01"}
    respx.get(f"{BASE}/v1/patients/pat_01").mock(
        return_value=httpx.Response(200, json=patient)
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        with pytest.warns(DeprecationWarning):
            result = client.patients.get("pat_01")

    assert result["id"] == "pat_01"


@respx.mock
def test_api_error_includes_detail():
    respx.get(f"{BASE}/v1/patients/bad").mock(
        return_value=httpx.Response(404, text="not found")
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        with pytest.warns(DeprecationWarning), pytest.raises(HebrahApiError) as exc:
            client.patients.get("bad")

    assert exc.value.status == 404
    assert exc.value.detail == "not found"


@respx.mock
def test_api_error_omits_detail_when_disabled():
    respx.get(f"{BASE}/v1/patients/bad").mock(
        return_value=httpx.Response(404, text="not found")
    )

    with HebrahClient(
        api_key="hb_test_key",
        base_url=BASE,
        include_error_detail=False,
    ) as client:
        with pytest.warns(DeprecationWarning), pytest.raises(HebrahApiError) as exc:
            client.patients.get("bad")

    assert exc.value.status == 404
    assert exc.value.detail is None


@respx.mock
def test_health_does_not_send_authorization_header():
    respx.get(f"{BASE}/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        client.health()

    assert "Authorization" not in respx.calls[0].request.headers


@respx.mock
def test_trigger_mock_event():
    body = {
        "status": "queued",
        "event": "patient.admitted",
        "patient_id": "pat_01",
        "connection_id": "conn-sa-1",
        "envelope_preview": {},
    }
    route = respx.post(f"{BASE}/v1/webhooks/trigger-mock-event").mock(
        return_value=httpx.Response(202, json=body)
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        result = client.webhooks.trigger_mock_event(
            event="patient.admitted",
            patient_id="pat_01",
        )

    assert result["status"] == "queued"
    assert json.loads(route.calls[0].request.content) == {
        "event": "patient.admitted",
        "patient_id": "pat_01",
    }


@respx.mock
def test_smart_launch_sends_api_key_bearer():
    respx.post(f"{BASE}/v1/smart/launch").mock(
        return_value=httpx.Response(200, json={"launch_url": "https://example.com"})
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        client.smart.launch(patient_id="pat_01")

    assert respx.calls[0].request.headers["Authorization"] == "Bearer hb_test_key"


@respx.mock
def test_smart_register_client_posts_to_clients_with_api_key():
    respx.post(f"{BASE}/v1/smart/clients").mock(
        return_value=httpx.Response(200, json={"client_id": "app-1"})
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        client.smart.register_client(
            client_id="app-1",
            redirect_uris=["https://app.example/callback"],
        )

    assert respx.calls[0].request.url.path == "/v1/smart/clients"
    assert respx.calls[0].request.headers["Authorization"] == "Bearer hb_test_key"


@respx.mock
def test_smart_exchange_token_posts_without_api_key():
    respx.post(f"{BASE}/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok", "token_type": "Bearer"})
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        client.smart.exchange_token(
            code="auth-code",
            redirect_uri="https://app.example/callback",
            client_id="app-1",
            code_verifier="verifier",
        )

    request = respx.calls[0].request
    assert request.url.path == "/oauth/token"
    assert request.headers.get("Authorization") is None
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"


@respx.mock
def test_fhir_methods_support_api_key_and_access_token():
    respx.get(f"{BASE}/fhir/R4/metadata").mock(
        return_value=httpx.Response(200, json={"resourceType": "CapabilityStatement"})
    )
    respx.get(f"{BASE}/fhir/R4/Patient/pat_01").mock(
        return_value=httpx.Response(200, json={"resourceType": "Patient", "id": "pat_01"})
    )
    respx.get(f"{BASE}/fhir/R4/Observation").mock(
        return_value=httpx.Response(200, json={"resourceType": "Bundle", "entry": []})
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        cap = client.fhir.metadata()
        assert cap["resourceType"] == "CapabilityStatement"
        assert respx.calls[0].request.headers["Authorization"] == "Bearer hb_test_key"

        # Explicit SMART access token overrides API key
        client.fhir.read_patient("pat_01", "smart-access-token")
        assert respx.calls[1].request.headers["Authorization"] == "Bearer smart-access-token"

        # Default API key when access_token omitted
        client.fhir.read_patient("pat_01")
        assert respx.calls[2].request.headers["Authorization"] == "Bearer hb_test_key"

        # Search with query params
        bundle = client.fhir.search("Observation", {"patient": "pat_01", "_count": 5})
        assert bundle["resourceType"] == "Bundle"
        assert respx.calls[3].request.url.params["patient"] == "pat_01"
        assert respx.calls[3].request.url.params["_count"] == "5"


def test_resolve_base_url_explicit():
    assert resolve_base_url("https://custom.example/") == "https://custom.example"


def test_resolve_base_url_env_fallback(monkeypatch):
    monkeypatch.setenv("HEBRAH_API_BASE_URL", "http://localhost:8000/")
    assert resolve_base_url() == "http://localhost:8000"


def test_resolve_base_url_rejects_unsafe_http_env(monkeypatch):
    monkeypatch.setenv("HEBRAH_API_BASE_URL", "http://evil.example.com")
    with pytest.raises(ValueError, match="base_url must use https"):
        resolve_base_url()


def test_verify_webhook_signature():
    secret = "hbsec_test"
    payload = {"event": "patient.admitted", "connection_id": "conn-1"}
    raw = json.dumps(payload).encode("utf-8")
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()

    parsed = verify_webhook_signature(raw, signature, secret)
    assert parsed["event"] == "patient.admitted"

    # Also supports sha256= prefix and uppercase hex
    parsed_prefixed = verify_webhook_signature(raw, f"sha256={signature.upper()}", secret)
    assert parsed_prefixed["event"] == "patient.admitted"


def test_verify_webhook_invalid_and_edge_cases():
    with pytest.raises(ValueError, match="webhook_secret is required"):
        verify_webhook_signature(b"{}", "sig", "")

    with pytest.raises(ValueError, match="Invalid webhook signature"):
        verify_webhook_signature(b"{}", "bad", "hbsec_test")

    with pytest.raises(ValueError, match="Missing X-Hebrah-Signature header"):
        verify_webhook_signature(b"{}", None, "hbsec_test")

    secret = "hbsec_test"
    raw = b"not-valid-json"
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    with pytest.raises(ValueError, match="Invalid webhook payload JSON"):
        verify_webhook_signature(raw, sig, secret)


@respx.mock
def test_environments_list_and_methods():
    respx.get(f"{BASE}/v1/environments").mock(
        return_value=httpx.Response(200, json=[{"id": "env-1", "name": "St. Jude Clinic"}])
    )
    respx.get(f"{BASE}/v1/environments/env-1/ehr/summary").mock(
        return_value=httpx.Response(200, json={"environment_id": "env-1", "total_patients": 42})
    )
    respx.get(f"{BASE}/v1/environments/env-1/logs").mock(
        return_value=httpx.Response(200, json=[{"id": "log-1", "event_type": "db.query"}])
    )
    respx.post(f"{BASE}/v1/environments/env-1/modules").mock(
        return_value=httpx.Response(200, json={"id": "mod-1", "module_type": "vector_qdrant"})
    )
    respx.delete(f"{BASE}/v1/environments/env-1/modules/vector_qdrant").mock(
        return_value=httpx.Response(204)
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE, environment_id="env-1") as client:
        envs = client.environments.list()
        assert len(envs) == 1

        summary = client.environments.get_ehr_summary()
        assert summary["total_patients"] == 42

        logs = client.environments.logs(limit=10, actor_type="agent")
        assert len(logs) == 1
        assert respx.calls[2].request.url.params["limit"] == "10"
        assert respx.calls[2].request.url.params["actor_type"] == "agent"

        # Single-arg add_module / remove_module using default environment_id
        mod = client.environments.add_module("vector_qdrant")
        assert mod["module_type"] == "vector_qdrant"
        client.environments.remove_module("vector_qdrant")

        # Positional 2-arg add_module / remove_module backward compatibility
        client.environments.add_module("env-1", "vector_qdrant")
        client.environments.remove_module("env-1", "vector_qdrant")


@respx.mock
def test_db_query_schema_and_tables():
    respx.post(f"{BASE}/v1/environments/env-123/db/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "rows": [{"id": "pat-01", "first_name": "James"}],
                "row_count": 1,
                "bytes_egressed": 65,
                "duration_ms": 2.5,
                "sql_executed": "SELECT * FROM patients WHERE status = $1",
            },
        )
    )
    respx.get(f"{BASE}/v1/environments/env-123/db/schema").mock(
        return_value=httpx.Response(
            200,
            json={
                "environment_id": "env-123",
                "addon": "postgres",
                "tables": [
                    {
                        "name": "patients",
                        "row_count": 25,
                        "columns": [{"name": "id", "type": "text", "nullable": False}],
                    }
                ],
            },
        )
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE, environment_id="env-123") as client:
        result = client.db.query("SELECT * FROM patients WHERE status = $1", params=["active"])
        assert result["row_count"] == 1
        payload = json.loads(respx.calls[0].request.content)
        assert payload["params"] == ["active"]

        tables = client.db.tables(addon="postgres")
        assert len(tables) == 1
        assert tables[0]["name"] == "patients"


@respx.mock
def test_connections_and_agent_resources():
    respx.get(f"{BASE}/v1/connections/targets").mock(
        return_value=httpx.Response(
            200,
            json={"targets": [{"id": "epic-sandbox", "name": "Epic"}], "total": 1},
        )
    )
    respx.get(f"{BASE}/v1/connections").mock(
        return_value=httpx.Response(
            200,
            json={"connections": [{"id": "conn-1", "status": "active"}]},
        )
    )
    respx.post(f"{BASE}/v1/connections/conn-1/execute").mock(
        return_value=httpx.Response(
            200,
            json={"connection_id": "conn-1", "operation": "fhir.read", "result": {}},
        )
    )
    respx.get(f"{BASE}/v1/connections/conn-1/audit/verify").mock(
        return_value=httpx.Response(
            200,
            json={"connection_id": "conn-1", "verified": True, "total_events": 4},
        )
    )
    respx.post(f"{BASE}/v1/connections/conn-1/revoke").mock(
        return_value=httpx.Response(200, json={"id": "conn-1", "status": "revoked"})
    )
    respx.get(f"{BASE}/v1/agent/wallet").mock(
        return_value=httpx.Response(200, json={"balance_cents": 500, "balance_usd": "$5.00"})
    )
    respx.get(f"{BASE}/v1/agent/usage").mock(
        return_value=httpx.Response(200, json={"queries_used": 12, "queries_limit": 1000})
    )
    respx.get(f"{BASE}/v1/agent/ledger").mock(
        return_value=httpx.Response(200, json={"entries": [{"id": "led-1", "amount_cents": 500}]})
    )

    with HebrahClient(
        api_key="hb_test_key",
        base_url=BASE,
        default_connection_id="conn-1",
    ) as client:
        targets = client.connections.targets(include_all=True)
        assert targets["total"] == 1
        assert respx.calls[0].request.url.params["include_all"] == "true"

        conns = client.connections.list()
        assert len(conns["connections"]) == 1

        exec_res = client.connections.execute("fhir.read", {"resource_type": "Patient"})
        assert exec_res["operation"] == "fhir.read"

        audit = client.connections.audit_verify()
        assert audit["verified"] is True

        revoked = client.connections.revoke()
        assert revoked["status"] == "revoked"

        wallet = client.agent.wallet()
        assert wallet["balance_cents"] == 500

        usage = client.agent.usage()
        assert usage["queries_used"] == 12

        ledger = client.agent.ledger(limit=5)
        assert len(ledger["entries"]) == 1
        assert respx.calls[7].request.url.params["limit"] == "5"
