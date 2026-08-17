# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `CONTRIBUTING.md` describing dev setup, scripts, public-API rules, and the release process.
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
- Issue templates (bug report, feature request, docs) and PR template under `.github/`.
- OSS discovery badges in README (License, PyPI version + downloads, Python engine, GitHub stars + issues).
- CI matrix now tests Python 3.10, 3.11, 3.12, and 3.13.

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

[Unreleased]: https://github.com/Hebrah-inc/hebrah-sdk-python/compare/v0.8.1...HEAD
[0.8.1]: https://github.com/Hebrah-inc/hebrah-sdk-python/releases/tag/sdk-python-v0.8.1
[0.8.0]: https://github.com/Hebrah-inc/hebrah-sdk-python/releases/tag/sdk-python-v0.8.0
[0.1.0]: https://github.com/Hebrah-inc/hebrah-sdk-python/releases/tag/sdk-python-v0.1.0