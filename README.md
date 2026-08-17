# hebrah

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![PyPI](https://img.shields.io/pypi/v/hebrah.svg)](https://pypi.org/project/hebrah/)
[![PyPI downloads](https://img.shields.io/pypi/dm/hebrah.svg)](https://pypi.org/project/hebrah/)
[![Python ≥3.10](https://img.shields.io/badge/python-%3E%3D3.10-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![GitHub stars](https://img.shields.io/github/stars/Hebrah-inc/hebrah-sdk-python.svg?style=social)](https://github.com/Hebrah-inc/hebrah-sdk-python)
[![GitHub issues](https://img.shields.io/github/issues/Hebrah-inc/hebrah-sdk-python.svg)](https://github.com/Hebrah-inc/hebrah-sdk-python/issues)

Official Python SDK for the [hebrah](https://hebrah.com) control plane API (hebrah-api).

## Install

```bash
pip install hebrah
```

Requires **Python 3.10+**.

## Quick start

```python
import os
from hebrah import HebrahClient, verify_webhook_signature

with HebrahClient(
    api_key=os.environ["HEBRAH_API_KEY"],
    default_connection_id=os.environ.get("HEBRAH_CONNECTION_ID"),
) as client:
    catalog = client.sandbox.catalog()
    patient_id = catalog["sample_patient_ids"][0]
    patient = client.sandbox.resource("Patient", patient_id)

    client.webhooks.trigger_mock_event(
        event="patient.admitted",
        patient_id=patient_id,
    )
```

> **v0.8:** `default_connection_id` is applied when sandbox methods omit `connection_id`. `client.patients.list()` / `get()` emit `DeprecationWarning` — use `sandbox.list_synthetic_resources("Patient")` instead.

### Webhook verification

```python
from hebrah import verify_webhook_signature

payload = verify_webhook_signature(
    request.get_data(),
    request.headers.get("X-Hebrah-Signature"),
    webhook_secret,
)
```

## Security

- Store `HEBRAH_API_KEY` and `HEBRAH_WEBHOOK_SECRET` in server-side environment variables or a secrets manager only — never expose them to browsers or commit `.env` files.
- The SDK does not persist credentials; they live in memory for the lifetime of each `HebrahClient` instance.
- `base_url` must be `https://` in production, or `http://localhost` / `http://127.0.0.1` for local dev — other `http://` hosts are rejected at construction to reduce API-key exfiltration risk.
- Treat `HebrahApiError.detail` as operator-only diagnostics. Do not log or return it to end users — it may contain internal paths or sensitive API error payloads. Set `include_error_detail=False` on `HebrahClient` to omit `detail` from errors.

See [SECURITY.md](./SECURITY.md) for supported versions and vulnerability reporting.

## API surface (v0.8)

### Sandbox & resources

| Method | Description |
|--------|-------------|
| `client.health()` | `GET /health` (no API key on separate httpx call) |
| `client.sandbox.catalog(connection_id=None)` | `GET /v1/sandbox/catalog` — uses `default_connection_id` when omitted |
| `client.sandbox.domains()` | `GET /v1/sandbox/domains` |
| `client.sandbox.domain(domain_id)` | `GET /v1/sandbox/domains/{id}` |
| `client.sandbox.list_synthetic_resources(resource_type, connection_id=None)` | `GET /v1/sandbox/resources/{type}` |
| `client.sandbox.resource(resource_type, resource_id, patient_id=None)` | `GET /v1/sandbox/resources/{type}/{id}` |
| `client.sandbox.run_scenario(scenario_id, ...)` | `POST /v1/sandbox/scenarios/{id}/run` |
| `client.sandbox.synthetic_ehr_profile(connection_id=...)` | `GET /v1/sandbox/synthetic-ehr/profile` |
| `client.sandbox.list_ehr_models()` | `GET /v1/sandbox/ehr-models` |
| `client.sandbox.reset_synthetic_ehr(connection_id=...)` | `POST /v1/sandbox/synthetic-ehr/reset` |
| `client.sandbox.payer_rules(payer_id)` | `GET /v1/sandbox/payer-rules/{id}` |
| `client.patients.list(connection_id=None)` | **Deprecated** — `GET /v1/patients` |
| `client.patients.get(id, connection_id=None)` | **Deprecated** — `GET /v1/patients/{id}` |

### HL7, webhooks, interop

| Method | Description |
|--------|-------------|
| `client.sandbox.hl7_templates()` | `GET /v1/sandbox/hl7/templates` |
| `client.sandbox.inject_hl7(...)` | `POST /v1/sandbox/hl7/inject` |
| `client.sandbox.configure_webhook_reliability(**profile)` | `PATCH /v1/sandbox/webhook-reliability` |
| `client.sandbox.run_webhook_reliability_scenario(scenario_id, ...)` | `POST /v1/sandbox/scenarios/{id}/run` (alias) |
| `client.sandbox.run_mpi_match(...)` | `POST /v1/sandbox/mpi/match` |
| `client.sandbox.run_aggregator_query(...)` | `POST /v1/sandbox/aggregator/query` |
| `client.sandbox.get_practitioner_credentialing(practitioner_id)` | `GET /v1/sandbox/credentialing/practitioners/{id}` |
| `client.webhooks.trigger_mock_event(...)` | `POST /v1/webhooks/trigger-mock-event` |
| `client.webhooks.list_deliveries(...)` | `GET /v1/webhooks/deliveries` |
| `client.webhooks.replay_delivery(delivery_id)` | `POST /v1/webhooks/deliveries/{id}/replay` |
| `verify_webhook_signature(raw_body, signature, secret)` | Local HMAC-SHA256 verify |

### SMART & FHIR

| Method | Description |
|--------|-------------|
| `client.smart.launch(...)` | `POST /v1/smart/launch` |
| `client.smart.register_client(...)` | `POST /v1/smart/clients` |
| `client.smart.exchange_token(...)` | `POST /oauth/token` (form-encoded; no API key) |
| `client.fhir.read_patient(patient_id, access_token)` | `GET /fhir/R4/Patient/{id}` (SMART access token) |

### Advanced: BYOM agent harness

`HebrahAgentHarness` is exported for bring-your-own-model EHR workflows (MCP + integration-agent). It is **not** part of the core integrator quick start — harness improvements are tracked separately from the core client.

## Configuration

| Variable | Description |
|----------|-------------|
| `HEBRAH_API_KEY` | Pass to `HebrahClient(api_key=...)` |
| `HEBRAH_API_BASE_URL` | Optional; default `https://api.hebrah.com` |
| `HEBRAH_CONNECTION_ID` | Optional; pass to `default_connection_id` for sandbox reads |
| `HEBRAH_WEBHOOK_SECRET` | For `verify_webhook_signature` |

## Docs

Full integrator reference: [hebrah-app `/docs/sdk`](https://app.hebrah.com/docs/sdk).

## Examples

Runnable Python snippets live in [`examples/`](./examples):

- [`catalog.py`](./examples/catalog.py) — fetch the sandbox catalog
- [`verify_webhook.py`](./examples/verify_webhook.py) — verify an `X-Hebrah-Signature`
- [`trigger_mock_event.py`](./examples/trigger_mock_event.py) — fire a mock event

## License

MIT
