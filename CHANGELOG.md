# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] — 2026-10-14

### Added

- **Isolated Health Environments (`client.environments`)**:
  - `get_ehr_summary(environment_id=None)` (`GET /v1/environments/{id}/ehr/summary`).
  - Optional `environment_id` fallback across `get()`, `get_ehr_summary()`, `get_vpn_config()`, `logs()`, `add_module()`, and `remove_module()`.
  - `logs()` now supports `limit` and `actor_type` filters.
- **Credential-Blind Database Pack (`client.db`)**:
  - `client.db.query()` now supports parameterized queries via `params=[...]`.
  - `client.db.schema(environment_id=None, *, addon=None)` (`GET /v1/environments/{id}/db/schema`).
  - `client.db.tables(environment_id=None, *, addon=None)` helper returning `list[DbTableSchema]`.
- **FHIR R4 (`client.fhir`)**:
  - `client.fhir.metadata(access_token=None)` (`GET /fhir/R4/metadata`).
  - `client.fhir.read(resource_type, resource_id, access_token=None)` (`GET /fhir/R4/{type}/{id}`).
  - `client.fhir.search(resource_type, params=None, access_token=None)` (`GET /fhir/R4/{type}`).
  - `client.fhir.read_patient(patient_id, access_token=None)` now defaults to the client API key when `access_token` is omitted.
- **Scoped Connections (`client.connections`)**:
  - `targets(include_all=False)`, `list()`, `get()`, `create()`, `execute()`, `audit_verify()`, and `revoke()`.
- **Agent Wallet & Metering (`client.agent`)**:
  - `wallet()`, `usage()`, and `ledger(limit=None)`.
- **Environment Variable Fallbacks**:
  - `HebrahClient()` automatically reads `HEBRAH_API_KEY`, `HEBRAH_ENVIRONMENT_ID`, and `HEBRAH_CONNECTION_ID` from `os.environ` when omitted.

### Security

- Added `safe_path_segment()` validation across all dynamic URL path segments in `HebrahClient` and `HebrahAgentHarness` to block path-traversal sequences (`.`, `..`) and control characters (`\r`, `\n`, `\0`).
- Added `assert_safe_token()` validation on `api_key`, SMART `access_token`, and `HebrahAgentHarness(pat=...)` to prevent HTTP header injection.
- Enforced `assert_safe_base_url()` on `HebrahAgentHarness` URLs (`mcp_url`, `integration_agent_url`, `dashboard_url`) and added `include_error_detail` support.
- Hardened `verify_webhook_signature()` to reject empty secrets, accept optional `sha256=` prefixes and uppercase hex signatures, and raise `ValueError("Invalid webhook payload JSON")` on malformed JSON.

## [0.8.1] — 2026-08-17

### Fixed

- CI publish path so the OIDC trusted-publishing job only runs after tests pass on tag push.

## [0.8.0] — 2026-08-01

### Added

- `default_connection_id` on `HebrahClient` — applied when sandbox methods omit `connection_id`.
- `HebrahAgentHarness` for BYOM / integration-agent workflows (exported but documented separately from the core quickstart).

### Changed

- **Deprecated:** `client.patients.list()` and `client.patients.get()`. Use
  `client.sandbox.list_synthetic_resources("Patient")` /
  `client.sandbox.resource("Patient", id)` instead.

### Security

- `base_url` constructor check: rejects `http://` URLs that are not `localhost` / `127.0.0.1` to reduce API-key exfiltration risk.
- New `include_error_detail` option to omit raw `detail` payloads from thrown `HebrahApiError`s.

## [0.1.0] — 2026-06-08

### Added

- Initial open-source release of `hebrah` on PyPI.
- Sandbox, HL7, webhook, SMART, and FHIR surface over `/v1/sandbox/*`, `/v1/webhooks/*`, `/v1/smart/*`, `/oauth/token`, `/fhir/R4/*`.
- `verify_webhook_signature(raw_body, signature_header, secret)` helper.

[Unreleased]: https://github.com/Hebrah-inc/hebrah-sdk-python/compare/sdk-python-v0.9.0...HEAD
[0.9.0]: https://github.com/Hebrah-inc/hebrah-sdk-python/releases/tag/sdk-python-v0.9.0
[0.8.1]: https://github.com/Hebrah-inc/hebrah-sdk-python/releases/tag/sdk-python-v0.8.1
[0.8.0]: https://github.com/Hebrah-inc/hebrah-sdk-python/releases/tag/sdk-python-v0.8.0
[0.1.0]: https://github.com/Hebrah-inc/hebrah-sdk-python/releases/tag/sdk-python-v0.1.0