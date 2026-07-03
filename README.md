# hebrah

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

## API surface (v0.8)

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
| `client.webhooks.trigger_mock_event(...)` | `POST /v1/webhooks/trigger-mock-event` |
| `verify_webhook_signature(raw_body, signature, secret)` | Local HMAC-SHA256 verify |

## Configuration

| Variable | Description |
|----------|-------------|
| `HEBRAH_API_KEY` | Pass to `HebrahClient(api_key=...)` |
| `HEBRAH_API_BASE_URL` | Optional; default `https://api.hebrah.com` |
| `HEBRAH_CONNECTION_ID` | Optional; pass to `default_connection_id` for sandbox reads |
| `HEBRAH_WEBHOOK_SECRET` | For `verify_webhook_signature` |

## Local development

```bash
export HEBRAH_API_BASE_URL=http://localhost:8000
export HEBRAH_API_KEY=hb_test_your_key
export HEBRAH_CONNECTION_ID=conn-sa-your_connection_id
```

Start hebrah-api: `docker compose up --build` in the [hebrah-api](https://github.com/Hebrah-inc/hebrah-api) repo.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
```

## Publishing

Tag releases as `sdk-python-v0.1.0` to trigger GitHub Actions publish to PyPI.

Configure **trusted publishing** (OIDC) on PyPI for this GitHub repository (recommended), or set the `PYPI_API_TOKEN` repository secret.

## Docs

Full integrator reference: [hebrah-app `/docs/sdk`](https://app.hebrah.com/docs/sdk).

## License

MIT
