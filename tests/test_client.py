import hashlib
import hmac
import json

import httpx
import pytest
import respx

from hebrah import HebrahApiError, HebrahClient, verify_webhook_signature

BASE = "https://api.test.local"


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
def test_get_patient():
    patient = {"resourceType": "Patient", "id": "pat_01"}
    respx.get(f"{BASE}/v1/patients/pat_01").mock(
        return_value=httpx.Response(200, json=patient)
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        result = client.patients.get("pat_01")

    assert result["id"] == "pat_01"


@respx.mock
def test_api_error():
    respx.get(f"{BASE}/v1/patients/bad").mock(
        return_value=httpx.Response(404, text="not found")
    )

    with HebrahClient(api_key="hb_test_key", base_url=BASE) as client:
        with pytest.raises(HebrahApiError) as exc:
            client.patients.get("bad")

    assert exc.value.status == 404


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


def test_requires_api_key():
    with pytest.raises(ValueError, match="api_key is required"):
        HebrahClient(api_key="")