# Publishing hebrah

## Prerequisites

1. PyPI account and project name `hebrah` registered (or use TestPyPI first).
2. Trusted publishing (OIDC) configured on PyPI for `Hebrah-inc/hebrah-sdk-python`, or repository secret `PYPI_API_TOKEN`.

## Release

```bash
git tag sdk-python-v0.1.0
git push origin main
git push origin sdk-python-v0.1.0
```

GitHub Actions publishes on tags matching `sdk-python-v*`.

## Local publish (optional)

```bash
pip install build twine
python -m build
twine upload dist/*
```

## Smoke test

```bash
pip install -e .
HEBRAH_API_BASE_URL=http://localhost:8000 HEBRAH_API_KEY=hb_test_your_key python -c "
import os
from hebrah import HebrahClient
with HebrahClient(api_key=os.environ['HEBRAH_API_KEY'], base_url='http://localhost:8000') as c:
    print(c.health(), c.patients.get('pat_00000000_01')['id'])
"
