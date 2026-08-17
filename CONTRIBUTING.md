# Contributing

Thanks for your interest in the `hebrah` Python SDK! This is the official
Python client for the hebrah control plane API.

## Development setup

Requirements: Python 3.10+, [`uv`](https://docs.astral.sh/uv/) or
`pip`/`hatch`/`pipx` for builds, and a local hebrah-api on port 8000 for
smoke testing.

```bash
git clone https://github.com/Hebrah-inc/hebrah-sdk-python.git
cd hebrah-sdk-python

# pick one:
pip install -e ".[dev]"
# or
uv pip install --system -e ".[dev]"
```

## Scripts

| Command | Purpose |
|---|---|
| `pytest` | Run the test suite |
| `ruff check src tests` | Lint |
| `ruff format` | Format |
| `python -m build` | Build sdist + wheel |

## Tests

`pytest` with HTTP mocking via `respx`. Add a test next to the file you are
changing. Tests must not hit the network.

```bash
pytest -q
```

## Public API rules

- Public exports live in `src/hebrah/__init__.py`. Don't re-export internals.
- New methods on `HebrahClient` should match the corresponding
  `/v1/sandbox/*` (or `/v1/webhooks/*`, `/v1/smart/*`, `/fhir/R4/*`) endpoint
  and include a matching typed return.
- Method naming: `snake_case`, no abbreviations. Sandbox methods read,
  webhook / write methods act.
- Mark deprecated methods with a `DeprecationWarning` (`warnings.warn`)
  in the implementation; keep them working for at least one minor version.

## Pull request process

1. Fork the repository and create a feature branch.
2. Run `ruff check src tests && pytest -q` — both must pass.
3. Update `README.md` if you added or changed public methods.
4. Add a `## Unreleased` entry to `CHANGELOG.md`.
5. Open a PR. CI will run lint, tests across Python 3.10–3.13, and
   `pip-audit --strict`.

## Coding style

- PEP 8 + `ruff` (line length 100, rules `E, F, I, UP`).
- Type hints on every public function. The package ships `py.typed`.
- Prefer `httpx` idioms (`client.get(...)` not raw `requests`).
- Prefer named keyword arguments over positional ones for public API calls.

## Adding a method

1. Add the implementation to the appropriate module
   (`src/hebrah/client.py`, `src/hebrah/webhooks.py`, etc.).
2. Add the typed `TypedDict` / `dataclass` for the response.
3. Re-export from `src/hebrah/__init__.py`.
4. Add a `respx`-mocked test in `tests/`.
5. Document in `README.md` under the relevant section.

## Reporting security issues

See [`SECURITY.md`](./SECURITY.md). Please report privately — do not open a
public issue.

## Releasing

Maintainers: see [`PUBLISHING.md`](./PUBLISHING.md) for the OIDC trusted
publishing flow. Releases are tag-driven (`sdk-python-vX.Y.Z`).

## License

By contributing, you agree that your contributions will be licensed under the
MIT License. See [`LICENSE`](./LICENSE).