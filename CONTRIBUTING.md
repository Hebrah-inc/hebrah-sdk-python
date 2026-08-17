# Contributing to hebrah-sdk-python

Thanks for your interest in the Hebrah Python SDK.

## Repo scope

This repo ships the official Python SDK for the Hebrah healthcare
connectivity platform — typed clients, webhook verification helpers,
and a sandbox/resource harness.

| Path | Purpose |
|------|---------|
| `src/hebrah/client.py` | `Hebrah` class — top-level entry point (mirrors `hebrah-sdk-node/src/client.ts`). |
| `src/hebrah/http.py` | `httpx`-based HTTP transport (timeout, retry, error mapping). |
| `src/hebrah/webhooks.py` | `verify_webhook_signature` helper. |
| `src/hebrah/harness.py` | Test-harness server (Stripe-style webhook replay). |
| `src/hebrah/errors.py` | Typed exception hierarchy. |
| `src/hebrah/types.py` | Public types (sandbox, connection, patient, observation, …). |
| `src/hebrah/__init__.py` | Barrel export. |
| `tests/` | Pytest suite (22 tests covering auth, error mapping, webhooks). |

It is **not** the control plane (see
[`hebrah-api`](https://github.com/Hebrah-inc/hebrah-api)) and it is **not**
the hosted MCP server (see
[`hebrah-mcp-host`](https://github.com/Hebrah-inc/hebrah-mcp-host)).

## Development setup

You need **Python 3.10 or newer** and **uv** (or pip in a venv).

```bash
# Recommended (uv)
uv venv
uv pip install -e ".[dev]"
pytest                     # or: uv run pytest

# Plain pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

`[dev]` extra pulls in `pytest`, `respx` (for httpx mocking), and `ruff`.

## Code style

- **Ruff** for lint + format. The config lives in `pyproject.toml`
  (`[tool.ruff]`, `[tool.ruff.lint]`). Run `ruff check .` and
  `ruff format .` before pushing.
- **Strict type hints** — every public function signature must be fully
  typed. `from __future__ import annotations` is fine for forward refs.
- **`httpx` is the only HTTP client** — don't add `requests`, `aiohttp`,
  or `urllib3` to `dependencies`. SDKs stay lean.
- **`dataclasses` or `TypedDict` over raw dicts** in public types.
- **Docstrings on every public symbol** — IDE intellisense and the
  rendered docs both read these. Match the existing tone (terse,
  imperative).

## Adding a new method

1. Add the implementation to `src/hebrah/client.py` (or whichever
   module fits).
2. Add the public type to `src/hebrah/types.py`.
3. Export it from `src/hebrah/__init__.py`.
4. Add a pytest in `tests/test_client.py` that exercises the happy
   path *and* at least one error case (401, 4xx with detail, 5xx,
   network).
5. Run `pytest`, `ruff check .`, and `ruff format --check .`.
6. Update the README's method table.

If the method has a counterpart in
[`hebrah-sdk-node`](https://github.com/Hebrah-inc/hebrah-sdk-node),
mirror its signature and error semantics — the two SDKs are designed
to be drop-in equivalents across runtimes.

## Adding a webhook event type

1. Add the type to `src/hebrah/types.py` (see `WebhookEvent` and
   friends).
2. Update `verify_webhook_signature`'s overload to accept it.
3. Add a test in `tests/test_client.py` using the harness in
   `src/hebrah/harness.py`.
4. Update `README.md`'s webhooks section.

## Pull requests

1. Fork the repo and create a branch.
2. Run `pytest`, `ruff check .`, and `ruff format --check .` before
   pushing.
3. Keep PRs scoped — one method / one type / one fix per PR is easier
   to review.
4. Reference any related issue or design doc.
5. CI runs `pytest`, `ruff check`, and a build smoke check
   (`python -m build`). PRs that break CI will be asked to fix before
   review.

## Release process

Releases are cut from `main` by the maintainers. The version in
`pyproject.toml` is bumped, a tag is created (`vX.Y.Z`), and the
publish pipeline (GitHub Actions) pushes to PyPI.

Please don't bump versions or push tags yourself — just open the PR.

## Security disclosures

See [SECURITY.md](./SECURITY.md). **Please don't** file public issues
for security bugs — email security@hebrah.com instead.