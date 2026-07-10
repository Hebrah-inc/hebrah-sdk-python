import hashlib
import hmac
import json

import httpx
import pytest
import respx

from hebrah import HebrahApiError, HebrahClient, verify_webhook_signature
from hebrah.types import resolve_base_url

BASE = "https://api.test.local"


def test_requires_api_key():
    with pytest.raises(ValueError, match="api_key is required"):
        HebrahClient(api_key="")


def test_allows_https_base_url():
    with HebrahClient(api_key="hb_test_key", base_url="https://api.hebrah.com") as client:
        assert client.base_url == "https://api.hebrah.com"


def test_allows_http_localhost_base_url():
    with HebrahClient(api_key="hb_test_key", base_url="http://localhost:8000") as client:
        assert client.base_url == "http://localhost:8000"


def test_rejects_non_local_http_base_url():
    with pytest.raises(ValueError, match="base_url must use https"):
        HebrahClient(api_key="hb_test_key", base_url="http://evil.example.com")


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
        result = client.patients.get("pat_01")

    assert result["id"] == "pat_01"


@respx.mock
def test_api_error_includes_detail():
    respx.get(f"{BASE}/v1/patients/bad").mock(
        return_value=httpx.Response(404, text="not found")
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        with pytest.raises(HebrahApiError) as exc:
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
        with pytest.raises(HebrahApiError) as exc:
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
def test_fhir_read_patient_uses_access_token_not_api_key():
    respx.get(f"{BASE}/fhir/R4/Patient/pat_01").mock(
        return_value=httpx.Response(200, json={"resourceType": "Patient", "id": "pat_01"})
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        client.fhir.read_patient("pat_01", "smart-access-token")

    assert respx.calls[0].request.headers["Authorization"] == "Bearer smart-access-token"
    assert "hb_test_key" not in respx.calls[0].request.headers["Authorization"]


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


def test_verify_webhook_invalid():
    with pytest.raises(ValueError, match="Invalid webhook signature"):
        verify_webhook_signature(b"{}", "bad", "hbsec_test")


def test_verify_webhook_missing_header():
    with pytest.raises(ValueError, match="Missing X-Hebrah-Signature header"):
        verify_webhook_signature(b"{}", None, "hbsec_test")


def test_verify_webhook_wrong_length_signature():
    secret = "hbsec_test"
    raw = b"{}"
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    truncated = signature[:-2]

    with pytest.raises(ValueError, match="Invalid webhook signature"):
        verify_webhook_signature(raw, truncated, secret)
