# hebrah

Official Python SDK for the [hebrah](https://hebrah.com) control plane API (hebrah-api).

## Install

```bash
pip install hebrah
```

Requires **Python 3.10+**.

## Quick start

```python
from hebrah import HebrahClient, verify_webhook_signature

with HebrahClient(api_key="hb_test_your_key") as client:
    patient = client.patients.get("pat_00000000_01")
    catalog = client.sandbox.catalog()

    client.webhooks.trigger_mock_event(
        event="patient.admitted",
        patient_id="pat_00000000_01",
    )
```

### Webhook verification

```python
from hebrah import verify_webhook_signature

payload = verify_webhook_signature(
    request.get_data(),
    request.headers.get("X-Hebrah-Signature"),
    webhook_secret,
)
```

## API surface (v0.1)

| Method | Description |
|--------|-------------|
| `client.health()` | `GET /health` (no API key on separate httpx call) |
| `client.sandbox.catalog(connection_id=None)` | `GET /v1/sandbox/catalog` |
| `client.patients.list()` | `GET /v1/patients` |
| `client.patients.get(id)` | `GET /v1/patients/{id}` |
| `client.webhooks.trigger_mock_event(event=..., patient_id=...)` | `POST /v1/webhooks/trigger-mock-event` |
| `verify_webhook_signature(raw_body, signature, secret)` | Local HMAC-SHA256 verify |

## Configuration

| Variable | Description |
|----------|-------------|
| `HEBRAH_API_KEY` | Pass to `HebrahClient(api_key=...)` |
| `HEBRAH_API_BASE_URL` | Optional; default `https://api.hebrah.com` |
| `HEBRAH_WEBHOOK_SECRET` | For `verify_webhook_signature` |

## Local development

```bash
export HEBRAH_API_BASE_URL=http://localhost:8000
export HEBRAH_API_KEY=hb_test_your_key
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
