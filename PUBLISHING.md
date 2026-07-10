# Publishing hebrah

## Prerequisites

1. PyPI account and project name `hebrah` registered (or use TestPyPI first).
2. **Preferred:** trusted publishing (OIDC) configured on PyPI for `Hebrah-inc/hebrah-sdk-python`, using the `pypi` GitHub Environment.
3. **Fallback:** set repository variable `PUBLISH_WITH_PYPI_TOKEN=true` and add `PYPI_API_TOKEN` as a secret on the `pypi` environment.

## Release

```bash
git tag sdk-python-v0.8.0
git push origin main
git push origin sdk-python-v0.8.0
```

GitHub Actions publishes on tags matching `sdk-python-v*`.

### Publish authentication

| Mode | Setup |
|------|--------|
| OIDC (default) | Configure PyPI trusted publishing; leave `PUBLISH_WITH_PYPI_TOKEN` unset or `false` |
| PyPI token fallback | Set repo variable `PUBLISH_WITH_PYPI_TOKEN=true` and `PYPI_API_TOKEN` secret on the `pypi` environment |

Do not set `TWINE_PASSWORD` unconditionally when using OIDC — it overrides the OIDC token and breaks publish.

## Local publish (optional)

```bash
pip install build twine
python -m build
twine upload dist/*
```

## Smoke test after publish

```bash
pip install hebrah==0.8.0
HEBRAH_API_BASE_URL=http://localhost:8000 HEBRAH_API_KEY=hb_test_your_key python scripts/smoke.py
```

## First-time PyPI setup checklist

1. Register the `hebrah` project on [pypi.org](https://pypi.org) if it does not exist.
2. Create GitHub Environment `pypi` on `Hebrah-inc/hebrah-sdk-python`.
3. Add trusted publishing: PyPI project settings → link GitHub repo `Hebrah-inc/hebrah-sdk-python`, workflow `CI`, environment `pypi`.
4. Make the GitHub repo **public** (referenced in `pyproject.toml` `Repository`).
5. Push tag `sdk-python-v0.8.0` and verify the package appears at `https://pypi.org/project/hebrah/`.
