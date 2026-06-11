from __future__ import annotations

from typing import Any

import httpx

from hebrah.errors import HebrahApiError
from hebrah.types import (
    PatientListResponse,
    SandboxCatalog,
    TriggerMockEventResponse,
    resolve_base_url,
)


class _SandboxResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def catalog(self, connection_id: str | None = None) -> SandboxCatalog:
        params = {"connection_id": connection_id} if connection_id else None
        return self._client._request("GET", "/v1/sandbox/catalog", params=params)


class _PatientsResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def list(self) -> PatientListResponse:
        return self._client._request("GET", "/v1/patients")

    def get(self, patient_id: str) -> dict[str, Any]:
        from urllib.parse import quote

        return self._client._request(
            "GET",
            f"/v1/patients/{quote(patient_id, safe='')}",
        )


class _WebhooksResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def trigger_mock_event(
        self,
        *,
        event: str,
        patient_id: str | None = None,
    ) -> TriggerMockEventResponse:
        body: dict[str, str] = {"event": event}
        if patient_id:
            body["patient_id"] = patient_id
        return self._client._request(
            "POST",
            "/v1/webhooks/trigger-mock-event",
            json=body,
        )


class HebrahClient:
    """Sync client for the hebrah control plane API."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")
        self._api_key = api_key.strip()
        self._base_url = resolve_base_url(base_url)
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )
        self.sandbox = _SandboxResource(self)
        self.patients = _PatientsResource(self)
        self.webhooks = _WebhooksResource(self)

    @property
    def base_url(self) -> str:
        return self._base_url

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> HebrahClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, str]:
        try:
            response = httpx.get(f"{self._base_url}/health", timeout=30.0)
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"Control plane unreachable at {self._base_url}. Is hebrah-api running?",
                503,
            ) from exc
        if not response.is_success:
            raise HebrahApiError(
                f"Health check failed ({response.status_code})",
                response.status_code,
                response.text,
            )
        return response.json()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, str] | None = None,
    ) -> Any:
        try:
            response = self._http.request(method, path, params=params, json=json)
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"Control plane unreachable at {self._base_url}. Is hebrah-api running?",
                503,
            ) from exc

        if not response.is_success:
            raise HebrahApiError(
                f"Control plane request failed ({response.status_code})",
                response.status_code,
                response.text,
            )

        if not response.content:
            return None
        return response.json()