from __future__ import annotations

import warnings
from typing import Any

import httpx

from hebrah.errors import HebrahApiError
from hebrah.types import (
    PatientListResponse,
    PayerRules,
    RunScenarioResponse,
    SandboxCatalog,
    SandboxDomainSummary,
    SandboxResourceListResponse,
    TriggerMockEventResponse,
    resolve_base_url,
)


class _SandboxResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def catalog(self, connection_id: str | None = None) -> SandboxCatalog:
        return self._client._request(
            "GET",
            "/v1/sandbox/catalog",
            params=self._client._connection_params(connection_id),
        )

    def domains(self) -> list[SandboxDomainSummary]:
        return self._client._request("GET", "/v1/sandbox/domains")

    def domain(self, domain_id: str) -> SandboxDomainSummary:
        from urllib.parse import quote

        return self._client._request(
            "GET",
            f"/v1/sandbox/domains/{quote(domain_id, safe='')}",
        )

    def resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        patient_id: str | None = None,
    ) -> dict[str, Any]:
        from urllib.parse import quote

        params = {"patient_id": patient_id} if patient_id else None
        return self._client._request(
            "GET",
            f"/v1/sandbox/resources/{quote(resource_type, safe='')}/{quote(resource_id, safe='')}",
            params=params,
        )

    def list_synthetic_resources(
        self,
        resource_type: str,
        *,
        connection_id: str | None = None,
    ) -> SandboxResourceListResponse:
        from urllib.parse import quote

        params = self._client._connection_params(connection_id)
        return self._client._request(
            "GET",
            f"/v1/sandbox/resources/{quote(resource_type, safe='')}",
            params=params,
        )

    def run_scenario(
        self,
        scenario_id: str,
        *,
        patient_id: str | None = None,
        connection_id: str | None = None,
        delay_seconds: float | None = None,
    ) -> RunScenarioResponse:
        from urllib.parse import quote

        body: dict[str, str | float] = {}
        if patient_id:
            body["patient_id"] = patient_id
        resolved_connection = self._client._resolve_connection_id(connection_id)
        if resolved_connection:
            body["connection_id"] = resolved_connection
        if delay_seconds is not None:
            body["delay_seconds"] = delay_seconds
        return self._client._request(
            "POST",
            f"/v1/sandbox/scenarios/{quote(scenario_id, safe='')}/run",
            json=body,
        )

    def payer_rules(self, payer_id: str) -> PayerRules:
        from urllib.parse import quote

        return self._client._request(
            "GET",
            f"/v1/sandbox/payer-rules/{quote(payer_id, safe='')}",
        )

    def hl7_templates(self) -> list[dict[str, Any]]:
        return self._client._request("GET", "/v1/sandbox/hl7/templates")

    def inject_hl7(
        self,
        *,
        message: str | None = None,
        template_id: str | None = None,
        patient_id: str | None = None,
        connection_id: str | None = None,
        event: str | None = None,
        deliver: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, str | bool] = {}
        if message:
            body["message"] = message
        if template_id:
            body["template_id"] = template_id
        if patient_id:
            body["patient_id"] = patient_id
        resolved_connection = self._client._resolve_connection_id(connection_id)
        if resolved_connection:
            body["connection_id"] = resolved_connection
        if event:
            body["event"] = event
        if deliver is not None:
            body["deliver"] = deliver
        return self._client._request("POST", "/v1/sandbox/hl7/inject", json=body)

    def configure_webhook_reliability(self, **profile: Any) -> dict[str, Any]:
        return self._client._request(
            "PATCH",
            "/v1/sandbox/webhook-reliability",
            json=profile,
        )

    def run_webhook_reliability_scenario(
        self,
        scenario_id: str,
        *,
        patient_id: str | None = None,
        connection_id: str | None = None,
    ) -> RunScenarioResponse:
        return self.run_scenario(
            scenario_id,
            patient_id=patient_id,
            connection_id=connection_id,
        )

    def run_mpi_match(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        birth_date: str | None = None,
        identifier: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, str] = {}
        if first_name:
            body["first_name"] = first_name
        if last_name:
            body["last_name"] = last_name
        if birth_date:
            body["birth_date"] = birth_date
        if identifier:
            body["identifier"] = identifier
        return self._client._request("POST", "/v1/sandbox/mpi/match", json=body)

    def run_aggregator_query(
        self,
        *,
        patient_id: str,
        include_consent: bool = True,
        include_provenance: bool = True,
    ) -> dict[str, Any]:
        return self._client._request(
            "POST",
            "/v1/sandbox/aggregator/query",
            json={
                "patient_id": patient_id,
                "include_consent": include_consent,
                "include_provenance": include_provenance,
            },
        )

    def get_practitioner_credentialing(self, practitioner_id: str) -> dict[str, Any]:
        from urllib.parse import quote

        return self._client._request(
            "GET",
            f"/v1/sandbox/credentialing/practitioners/{quote(practitioner_id, safe='')}",
        )

    def synthetic_ehr_profile(self, *, connection_id: str | None = None) -> dict[str, Any]:
        return self._client._request(
            "GET",
            "/v1/sandbox/synthetic-ehr/profile",
            params=self._client._connection_params(connection_id),
        )

    def list_ehr_models(self) -> list[dict[str, Any]]:
        return self._client._request("GET", "/v1/sandbox/ehr-models")

    def reset_synthetic_ehr(self, *, connection_id: str | None = None) -> dict[str, Any]:
        return self._client._request(
            "POST",
            "/v1/sandbox/synthetic-ehr/reset",
            params=self._client._connection_params(connection_id),
        )


class _SmartResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def launch(
        self,
        *,
        patient_id: str,
        encounter_id: str | None = None,
        smart_app_url: str | None = None,
    ) -> dict[str, Any]:
        return self._client._request(
            "POST",
            "/v1/smart/launch",
            json={
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "smart_app_url": smart_app_url,
            },
        )

    def register_client(
        self,
        *,
        client_id: str,
        redirect_uris: list[str],
        name: str | None = None,
    ) -> dict[str, Any]:
        return self._client._request(
            "POST",
            "/v1/smart/clients",
            json={
                "client_id": client_id,
                "name": name or "Python SDK SMART client",
                "redirect_uris": redirect_uris,
            },
        )

    def exchange_token(
        self,
        *,
        code: str,
        redirect_uri: str,
        client_id: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        response = httpx.post(
            f"{self._client._base_url}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
        if not response.is_success:
            raise HebrahApiError(
                f"SMART token exchange failed ({response.status_code})",
                response.status_code,
                response.text,
            )
        return response.json()


class _FhirResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def read_patient(self, patient_id: str, access_token: str) -> dict[str, Any]:
        from urllib.parse import quote

        response = httpx.get(
            f"{self._client._base_url}/fhir/R4/Patient/{quote(patient_id, safe='')}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/fhir+json",
            },
            timeout=30.0,
        )
        if not response.is_success:
            raise HebrahApiError(
                f"FHIR Patient read failed ({response.status_code})",
                response.status_code,
                response.text,
            )
        return response.json()


class _PatientsResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def list(self, *, connection_id: str | None = None) -> PatientListResponse:
        warnings.warn(
            "patients.list() is deprecated; use sandbox.list_synthetic_resources('Patient', connection_id=...).",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._client._request(
            "GET",
            "/v1/patients",
            params=self._client._connection_params(connection_id),
        )

    def get(self, patient_id: str, *, connection_id: str | None = None) -> dict[str, Any]:
        warnings.warn(
            "patients.get() is deprecated; use sandbox.resource('Patient', patient_id) for connection-scoped reads.",
            DeprecationWarning,
            stacklevel=2,
        )
        from urllib.parse import quote

        return self._client._request(
            "GET",
            f"/v1/patients/{quote(patient_id, safe='')}",
            params=self._client._connection_params(connection_id),
        )


class _WebhooksResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def trigger_mock_event(
        self,
        *,
        event: str | None = None,
        patient_id: str | None = None,
        connection_id: str | None = None,
        domain_id: str | None = None,
        scenario_id: str | None = None,
    ) -> TriggerMockEventResponse:
        body: dict[str, str] = {}
        if event:
            body["event"] = event
        if patient_id:
            body["patient_id"] = patient_id
        resolved_connection = self._client._resolve_connection_id(connection_id)
        if resolved_connection:
            body["connection_id"] = resolved_connection
        if domain_id:
            body["domain_id"] = domain_id
        if scenario_id:
            body["scenario_id"] = scenario_id
        return self._client._request(
            "POST",
            "/v1/webhooks/trigger-mock-event",
            json=body,
        )

    def list_deliveries(
        self,
        *,
        connection_id: str | None = None,
        status: str | None = None,
        event: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        params: dict[str, str] = {}
        resolved_connection = self._client._resolve_connection_id(connection_id)
        if resolved_connection:
            params["connection_id"] = resolved_connection
        if status:
            params["status"] = status
        if event:
            params["event"] = event
        if limit is not None:
            params["limit"] = str(limit)
        return self._client._request("GET", "/v1/webhooks/deliveries", params=params or None)

    def replay_delivery(self, delivery_id: str) -> dict[str, Any]:
        from urllib.parse import quote

        return self._client._request(
            "POST",
            f"/v1/webhooks/deliveries/{quote(delivery_id, safe='')}/replay",
        )


class HebrahClient:
    """Sync client for the hebrah control plane API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        default_connection_id: str | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")
        self._api_key = api_key.strip()
        self._base_url = resolve_base_url(base_url)
        self._default_connection_id = default_connection_id.strip() if default_connection_id else None
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )
        self.sandbox = _SandboxResource(self)
        self.patients = _PatientsResource(self)
        self.webhooks = _WebhooksResource(self)
        self.smart = _SmartResource(self)
        self.fhir = _FhirResource(self)

    @property
    def base_url(self) -> str:
        return self._base_url

    def _resolve_connection_id(self, connection_id: str | None) -> str | None:
        return connection_id or self._default_connection_id

    def _connection_params(self, connection_id: str | None = None) -> dict[str, str] | None:
        resolved = self._resolve_connection_id(connection_id)
        return {"connection_id": resolved} if resolved else None

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
        json: dict[str, str | float | bool] | None = None,
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
