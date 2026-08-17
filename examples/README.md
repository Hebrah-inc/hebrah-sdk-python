# `hebrah` examples

Runnable Python snippets that exercise the most common control-plane
endpoints. Every example reads its credentials from environment variables
(never hard-coded) and exits non-zero if a required var is missing.

| File | What it shows |
|------|---------------|
| `catalog.py` | Connect, fetch the sandbox catalog, print org + connection + sample IDs. |
| `verify_webhook.py` | Verify an `X-Hebrah-Signature` header against a raw body using `verify_webhook_signature`. |
| `trigger_mock_event.py` | Trigger a mock webhook event against a sandbox connection. |

## Running

Install the SDK in editable mode (with `[dev]` for any helpers used in
tests):

```bash
pip install -e ".[dev]"
```

Then run any example:

```bash
HEBRAH_API_KEY=hb_test_your_key \
HEBRAH_API_BASE_URL=http://localhost:8000 \
python examples/catalog.py
```

Each example documents its own required environment variables and optional
overrides.

## Pointing at staging vs local

- Local dev (hebrah-api on `:8000`): `HEBRAH_API_BASE_URL=http://localhost:8000`
- Staging: omit `HEBRAH_API_BASE_URL` (defaults to `https://api.hebrah.com`)