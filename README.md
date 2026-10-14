# hebrah

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![PyPI](https://img.shields.io/pypi/v/hebrah.svg)](https://pypi.org/project/hebrah/)
[![PyPI downloads](https://img.shields.io/pypi/dm/hebrah.svg)](https://pypi.org/project/hebrah/)
[![Python ≥3.10](https://img.shields.io/badge/python-%3E%3D3.10-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![GitHub stars](https://img.shields.io/github/stars/Hebrah-inc/hebrah-sdk-python.svg?style=social)](https://github.com/Hebrah-inc/hebrah-sdk-python)
[![GitHub issues](https://img.shields.io/github/issues/Hebrah-inc/hebrah-sdk-python.svg)](https://github.com/Hebrah-inc/hebrah-sdk-python/issues)

Official Python SDK for the [hebrah](https://hebrah.com) Isolated Health Environments & Connectivity Control Plane (`hebrah-api`).

## Install

```bash
pip install hebrah
```

Requires **Python 3.10+**.

## Quick start (Isolated Health Environments)

`HebrahClient` automatically resolves `HEBRAH_API_KEY`, `HEBRAH_ENVIRONMENT_ID`, `HEBRAH_CONNECTION_ID`, and `HEBRAH_API_BASE_URL` from environment variables when omitted.

```python
from hebrah import HebrahClient

# Automatically reads HEBRAH_API_KEY and HEBRAH_ENVIRONMENT_ID from os.environ
with HebrahClient() as client:
    # 1. Inspect attached database module schema (PostgreSQL 16, SQLite, etc.)
    schema = client.db.schema()

    # 2. Execute a credential-blind parameterized SQL query
    result = client.db.query(
        "SELECT id, first_name, last_name, mrn FROM patients WHERE status = $1 LIMIT 10",
        params=["active"],
    )
    print(f"Returned {result['row_count']} rows:")
    for row in result["rows"]:
        print(row)

    # 3. Read FHIR R4 resources directly using your API key or SMART token
    bundle = client.fhir.search("Patient", {"_count": 5})

    # 4. Inspect environment EHR summary & hash-chained audit logs
    ehr = client.environments.get_ehr_summary()
    logs = client.environments.logs(limit=20)
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

## Security

- Store `HEBRAH_API_KEY` and `HEBRAH_WEBHOOK_SECRET` in server-side environment variables or a secrets manager only — never expose them to browsers or commit `.env` files.
- The SDK does not persist credentials; they live in memory for the lifetime of each `HebrahClient` instance.
- `base_url` (and `HebrahAgentHarness` endpoints) must use `https://` in production, or `http://localhost` / `http://127.0.0.1` for local dev — other `http://` hosts are rejected at construction to prevent API-key exfiltration.
- All dynamic URL path segments are validated against path-traversal sequences (`.`, `..`, control characters) and percent-encoded.
- Treat `HebrahApiError.detail` as operator-only diagnostics. Do not log or return it to end users — it may contain internal paths or sensitive API error payloads. Set `include_error_detail=False` on `HebrahClient` to omit `detail` from errors.

See [SECURITY.md](./SECURITY.md) for supported versions and vulnerability reporting.

## API surface (v0.9)

### Isolated Health Environments (`client.environments`)

| Method | Description |
|--------|-------------|
| `client.environments.list()` | `GET /v1/environments` — list isolated clinic environments |
| `client.environments.create(...)` | `POST /v1/environments` — provision a new clinic environment |
| `client.environments.get(environment_id=None)` | `GET /v1/environments/{id}` — defaults to `environment_id` |
| `client.environments.update_status(environment_id, status)` | `PATCH /v1/environments/{id}/status` (`active`, `paused`, `archived`) |
| `client.environments.get_ehr_summary(environment_id=None)` | `GET /v1/environments/{id}/ehr/summary` |
| `client.environments.add_module(...)` | `POST /v1/environments/{id}/modules` (`postgres`, `sqlite`, `vector_qdrant`, `graph_neo4j`) |
| `client.environments.remove_module(...)` | `DELETE /v1/environments/{id}/modules/{type}` |
| `client.environments.get_vpn_config(environment_id=None)` | `GET /v1/environments/{id}/vpn/config` — WireGuard `.conf` tunnel |
| `client.environments.logs(environment_id=None, *, limit=None, actor_type=None)` | `GET /v1/environments/{id}/logs` — hash-chained audit logs |

### Credential-Blind Database Queries (`client.db`)

| Method | Description |
|--------|-------------|
| `client.db.query(sql, *, params=None, addon="postgres", actor_type="agent", environment_id=None)` | `POST /v1/environments/{id}/db/query` |
| `client.db.schema(environment_id=None, *, addon=None)` | `GET /v1/environments/{id}/db/schema` |
| `client.db.tables(environment_id=None, *, addon=None)` | Returns `list[DbTableSchema]` for the environment database |

### FHIR R4 & SMART on FHIR (`client.fhir`, `client.smart`)

| Method | Description |
|--------|-------------|
| `client.fhir.metadata(access_token=None)` | `GET /fhir/R4/metadata` — FHIR CapabilityStatement |
| `client.fhir.read(resource_type, resource_id, access_token=None)` | `GET /fhir/R4/{type}/{id}` (uses API key or SMART token) |
| `client.fhir.search(resource_type, params=None, access_token=None)` | `GET /fhir/R4/{type}` — FHIR search bundle |
| `client.fhir.read_patient(patient_id, access_token=None)` | `GET /fhir/R4/Patient/{id}` |
| `client.smart.launch(...)` | `POST /v1/smart/launch` |
| `client.smart.register_client(...)` | `POST /v1/smart/clients` |
| `client.smart.exchange_token(...)` | `POST /oauth/token` (form-encoded; no API key) |

### Scoped Connections & Audit (`client.connections`)

| Method | Description |
|--------|-------------|
| `client.connections.targets(include_all=False)` | `GET /v1/connections/targets` — list connector pack targets |
| `client.connections.list()` | `GET /v1/connections` — list scoped connections |
| `client.connections.get(connection_id=None)` | `GET /v1/connections/{id}` |
| `client.connections.create(target_id, scopes=None, mode=None, display_name=None, credentials=None)` | `POST /v1/connections` |
| `client.connections.execute(operation, params=None, *, connection_id=None)` | `POST /v1/connections/{id}/execute` |
| `client.connections.audit_verify(connection_id=None)` | `GET /v1/connections/{id}/audit/verify` — verify SHA-256 hash chain |
| `client.connections.revoke(connection_id=None)` | `POST /v1/connections/{id}/revoke` |

### Agent Wallet & Metering (`client.agent`)

| Method | Description |
|--------|-------------|
| `client.agent.wallet()` | `GET /v1/agent/wallet` — credit balance & trial status |
| `client.agent.usage()` | `GET /v1/agent/usage` — metered queries & egress usage |
| `client.agent.ledger(limit=None)` | `GET /v1/agent/ledger` — credit/debit ledger entries |

### Sandbox, HL7 & Webhooks (`client.sandbox`, `client.webhooks`)

| Method | Description |
|--------|-------------|
| `client.health()` | `GET /health` (no API key on separate httpx call) |
| `client.sandbox.catalog(connection_id=None)` | `GET /v1/sandbox/catalog` |
| `client.sandbox.domains()` | `GET /v1/sandbox/domains` |
| `client.sandbox.domain(domain_id)` | `GET /v1/sandbox/domains/{id}` |
| `client.sandbox.list_synthetic_resources(resource_type, connection_id=None)` | `GET /v1/sandbox/resources/{type}` |
| `client.sandbox.resource(resource_type, resource_id, patient_id=None)` | `GET /v1/sandbox/resources/{type}/{id}` |
| `client.sandbox.run_scenario(scenario_id, ...)` | `POST /v1/sandbox/scenarios/{id}/run` |
| `client.sandbox.synthetic_ehr_profile(connection_id=...)` | `GET /v1/sandbox/synthetic-ehr/profile` |
| `client.sandbox.list_ehr_models()` | `GET /v1/sandbox/ehr-models` |
| `client.sandbox.reset_synthetic_ehr(connection_id=...)` | `POST /v1/sandbox/synthetic-ehr/reset` |
| `client.sandbox.payer_rules(payer_id)` | `GET /v1/sandbox/payer-rules/{id}` |
| `client.sandbox.hl7_templates()` | `GET /v1/sandbox/hl7/templates` |
| `client.sandbox.inject_hl7(...)` | `POST /v1/sandbox/hl7/inject` |
| `client.webhooks.trigger_mock_event(...)` | `POST /v1/webhooks/trigger-mock-event` |
| `client.webhooks.list_deliveries(...)` | `GET /v1/webhooks/deliveries` |
| `client.webhooks.replay_delivery(delivery_id)` | `POST /v1/webhooks/deliveries/{id}/replay` |
| `verify_webhook_signature(raw_body, signature, secret)` | Local HMAC-SHA256 verify |

## Configuration

| Variable | Description |
|----------|-------------|
| `HEBRAH_API_KEY` | Automatic fallback when `api_key` is omitted on `HebrahClient()` |
| `HEBRAH_ENVIRONMENT_ID` | Automatic fallback for `environment_id` on `HebrahClient()` |
| `HEBRAH_CONNECTION_ID` | Automatic fallback for `default_connection_id` on `HebrahClient()` |
| `HEBRAH_API_BASE_URL` | Optional; default `https://api.hebrah.com` |
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
