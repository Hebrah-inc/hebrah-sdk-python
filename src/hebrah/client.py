from __future__ import annotations

import os
import warnings
from typing import Any

import httpx

from hebrah.errors import HebrahApiError
from hebrah.types import (
    AgentLedgerResponse,
    AgentUsageSummary,
    AgentWalletSummary,
    AuditVerifyResponse,
    ConnectionListResponse,
    ConnectionTargetsResponse,
    DbQueryResponse,
    DbSchemaResponse,
    DbTableSchema,
    EhrSummaryResponse,
    EnvironmentDetail,
    EnvironmentLogItem,
    EnvironmentSummary,
    ExecuteOperationResponse,
    PatientListResponse,
    PayerRules,
    RevokeConnectionResponse,
    RunScenarioResponse,
    SandboxCatalog,
    SandboxDomainSummary,
    SandboxResourceListResponse,
    ScopedConnection,
    TriggerClinicScenarioResponse,
    TriggerMockEventResponse,
    WireguardConfigResponse,
    assert_safe_token,
    resolve_base_url,
    safe_path_segment,
)


class _EnvironmentsResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def list(self) -> list[EnvironmentSummary]:
        return self._client._request("GET", "/v1/environments")

    def get(self, environment_id: str | None = None) -> EnvironmentDetail:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("GET", f"/v1/environments/{env_id}")

    def create(
        self,
        name: str,
        *,
        clinic_type: str = "general_clinic",
        patient_cohort: str = "geriatric",
        patient_count: int = 25,
        bed_count: int = 40,
        addons: list[str] | None = None,
    ) -> EnvironmentSummary:
        body: dict[str, Any] = {
            "name": name,
            "clinic_type": clinic_type,
            "patient_cohort": patient_cohort,
            "patient_count": patient_count,
            "bed_count": bed_count,
            "addons": addons if addons is not None else ["postgres"],
        }
        return self._client._request("POST", "/v1/environments", json=body)

    def pause(self, environment_id: str | None = None) -> EnvironmentSummary:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("POST", f"/v1/environments/{env_id}/pause")

    def resume(self, environment_id: str | None = None) -> EnvironmentSummary:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("POST", f"/v1/environments/{env_id}/resume")

    def destroy(self, environment_id: str | None = None) -> dict[str, Any]:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("DELETE", f"/v1/environments/{env_id}")

    def add_module(
        self,
        environment_id_or_module_type: str,
        module_type: str | None = None,
        *,
        environment_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if module_type is not None:
            resolved_env = environment_id_or_module_type
            resolved_module_type = module_type
        else:
            resolved_env = self._client._resolve_environment_id(environment_id)
            resolved_module_type = environment_id_or_module_type

        env_id = safe_path_segment(resolved_env, "environment_id")
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/modules",
            json={"module_type": resolved_module_type, "config": config or {}},
        )

    def remove_module(
        self,
        environment_id_or_module_id: str,
        module_id: str | None = None,
        *,
        environment_id: str | None = None,
    ) -> dict[str, Any]:
        if module_id is not None:
            resolved_env = environment_id_or_module_id
            resolved_module_id = module_id
        else:
            resolved_env = self._client._resolve_environment_id(environment_id)
            resolved_module_id = environment_id_or_module_id

        env_id = safe_path_segment(resolved_env, "environment_id")
        mod_id = safe_path_segment(resolved_module_id, "module_id")
        return self._client._request(
            "DELETE",
            f"/v1/environments/{env_id}/modules/{mod_id}",
        )

    def wireguard_config(self, environment_id: str | None = None) -> WireguardConfigResponse:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("GET", f"/v1/environments/{env_id}/wireguard/config")

    def get_ehr_summary(self, environment_id: str | None = None) -> EhrSummaryResponse:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("GET", f"/v1/environments/{env_id}/ehr/summary")

    def list_patients(self, environment_id: str | None = None) -> list[dict[str, Any]]:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("GET", f"/v1/environments/{env_id}/ehr/patients")

    def get_patient_chart(
        self,
        patient_id: str,
        *,
        environment_id: str | None = None,
    ) -> dict[str, Any]:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        pat_id = safe_path_segment(patient_id, "patient_id")
        return self._client._request(
            "GET",
            f"/v1/environments/{env_id}/ehr/patients/{pat_id}",
        )

    def trigger_scenario(
        self,
        scenario: str,
        *,
        environment_id: str | None = None,
        patient_id: str | None = None,
        notes: str | None = None,
    ) -> TriggerClinicScenarioResponse:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {"scenario": scenario}
        if patient_id:
            body["patient_id"] = patient_id
        if notes:
            body["notes"] = notes
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/ehr/scenarios/trigger",
            json=body,
        )

    def logs(
        self,
        environment_id: str | None = None,
        *,
        limit: int | None = None,
        actor_type: str | None = None,
    ) -> list[EnvironmentLogItem]:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        params: dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        if actor_type:
            params["actor_type"] = actor_type
        return self._client._request(
            "GET",
            f"/v1/environments/{env_id}/logs",
            params=params or None,
        )


class _DbResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def query(
        self,
        sql: str,
        *,
        addon: str = "postgres",
        actor_type: str = "agent",
        environment_id: str | None = None,
        params: list[Any] | None = None,
    ) -> DbQueryResponse:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {
            "sql": sql,
            "addon": addon,
            "actor_type": actor_type,
        }
        if params is not None:
            body["params"] = params
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/db/query",
            json=body,
        )

    def schema(
        self,
        environment_id: str | None = None,
        *,
        addon: str | None = None,
    ) -> DbSchemaResponse:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        params = {"addon": addon} if addon else None
        return self._client._request(
            "GET",
            f"/v1/environments/{env_id}/db/schema",
            params=params,
        )

    def tables(
        self,
        environment_id: str | None = None,
        *,
        addon: str = "postgres",
    ) -> list[DbTableSchema]:
        res = self.schema(environment_id=environment_id, addon=addon)
        return res.get("tables", []) if isinstance(res, dict) else []


class _ConnectionsResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def _require_connection_id(self, connection_id: str | None) -> str:
        resolved = self._client._resolve_connection_id(connection_id)
        if not resolved or not resolved.strip():
            raise ValueError(
                "connection_id is required (pass as argument or set default_connection_id)"
            )
        return safe_path_segment(resolved, "connection_id")

    def targets(
        self,
        *,
        pack_id: str | None = None,
        mode: str | None = None,
        include_incubating: bool = False,
        include_all: bool = False,
    ) -> ConnectionTargetsResponse:
        params: dict[str, str] = {}
        if pack_id:
            params["pack_id"] = pack_id
        if mode:
            params["mode"] = mode
        if include_incubating:
            params["include_incubating"] = "true"
        if include_all:
            params["include_all"] = "true"
        return self._client._request(
            "GET",
            "/v1/connections/targets",
            params=params or None,
        )

    def list(self, *, include_revoked: bool = False) -> ConnectionListResponse:
        params = {"include_revoked": "true"} if include_revoked else None
        return self._client._request("GET", "/v1/connections", params=params)

    def get(self, connection_id: str | None = None) -> ScopedConnection:
        conn_id = self._require_connection_id(connection_id)
        return self._client._request("GET", f"/v1/connections/{conn_id}")

    def create(
        self,
        target: str | None = None,
        *,
        target_id: str | None = None,
        scopes: list[str] | None = None,
        mode: str = "demo",
        purpose: str | None = None,
        display_name: str | None = None,
        agent_id: str | None = None,
        credentials: dict[str, Any] | None = None,
        relay_id: str | None = None,
    ) -> ScopedConnection:
        resolved_target = target or target_id
        if not resolved_target:
            raise ValueError("target is required")
        body: dict[str, Any] = {
            "target": resolved_target,
            "scopes": scopes or [],
            "mode": mode,
        }
        if purpose is not None:
            body["purpose"] = purpose
        elif display_name is not None:
            body["purpose"] = display_name
        if agent_id is not None:
            body["agent_id"] = agent_id
        if credentials is not None:
            body["credentials"] = credentials
        if relay_id is not None:
            body["relay_id"] = relay_id
        return self._client._request("POST", "/v1/connections", json=body)

    def execute(
        self,
        arg1: str,
        arg2: dict[str, Any] | None = None,
        *,
        operation: str | None = None,
        params: dict[str, Any] | None = None,
        connection_id: str | None = None,
    ) -> ExecuteOperationResponse:
        if operation is not None:
            conn_id = self._require_connection_id(arg1)
            op = operation
            op_params = params if params is not None else (arg2 or {})
        else:
            conn_id = self._require_connection_id(connection_id)
            op = arg1
            op_params = arg2 if arg2 is not None else (params or {})
        return self._client._request(
            "POST",
            f"/v1/connections/{conn_id}/execute",
            json={"operation": op, "params": op_params},
        )

    def audit_verify(self, connection_id: str | None = None) -> AuditVerifyResponse:
        conn_id = self._require_connection_id(connection_id)
        return self._client._request("GET", f"/v1/connections/{conn_id}/audit/verify")

    def revoke(
        self,
        connection_id: str | None = None,
        *,
        reason: str | None = None,
    ) -> RevokeConnectionResponse:
        conn_id = self._require_connection_id(connection_id)
        params = {"reason": reason} if reason else None
        return self._client._request(
            "POST",
            f"/v1/connections/{conn_id}/revoke",
            params=params,
        )


class _AgentResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def wallet(self) -> AgentWalletSummary:
        return self._client._request("GET", "/v1/agent/wallet")

    def usage(self) -> AgentUsageSummary:
        return self._client._request("GET", "/v1/agent/usage")

    def ledger(self, limit: int | None = None) -> AgentLedgerResponse:
        params = {"limit": str(limit)} if limit is not None else None
        return self._client._request("GET", "/v1/agent/ledger", params=params)


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
        dom_id = safe_path_segment(domain_id, "domain_id")
        return self._client._request(
            "GET",
            f"/v1/sandbox/domains/{dom_id}",
        )

    def resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        patient_id: str | None = None,
    ) -> dict[str, Any]:
        res_type = safe_path_segment(resource_type, "resource_type")
        res_id = safe_path_segment(resource_id, "resource_id")
        params = {"patient_id": patient_id} if patient_id else None
        return self._client._request(
            "GET",
            f"/v1/sandbox/resources/{res_type}/{res_id}",
            params=params,
        )

    def list_synthetic_resources(
        self,
        resource_type: str,
        *,
        connection_id: str | None = None,
    ) -> SandboxResourceListResponse:
        res_type = safe_path_segment(resource_type, "resource_type")
        params = self._client._connection_params(connection_id)
        return self._client._request(
            "GET",
            f"/v1/sandbox/resources/{res_type}",
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
        scen_id = safe_path_segment(scenario_id, "scenario_id")
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
            f"/v1/sandbox/scenarios/{scen_id}/run",
            json=body,
        )

    def payer_rules(self, payer_id: str) -> PayerRules:
        pid = safe_path_segment(payer_id, "payer_id")
        return self._client._request(
            "GET",
            f"/v1/sandbox/payer-rules/{pid}",
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
        prac_id = safe_path_segment(practitioner_id, "practitioner_id")
        return self._client._request(
            "GET",
            f"/v1/sandbox/credentialing/practitioners/{prac_id}",
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
        try:
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
        except httpx.TimeoutException as exc:
            raise HebrahApiError("SMART token exchange timed out", 504) from exc
        except httpx.RequestError as exc:
            raise HebrahApiError(
                "SMART token exchange failed: control plane unreachable",
                503,
            ) from exc
        if not response.is_success:
            raise HebrahApiError(
                f"SMART token exchange failed ({response.status_code})",
                response.status_code,
                self._client._error_detail(response.text),
            )
        return response.json()


class _FhirResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def _fhir_get(
        self,
        path: str,
        *,
        access_token: str | None = None,
        params: dict[str, str | int | bool] | None = None,
        error_prefix: str = "FHIR request",
    ) -> dict[str, Any]:
        token = (
            assert_safe_token(access_token, "access_token")
            if access_token is not None
            else self._client._api_key
        )
        str_params = {k: str(v) for k, v in params.items()} if params else None
        try:
            response = httpx.get(
                f"{self._client._base_url}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/fhir+json",
                },
                params=str_params,
                timeout=30.0,
            )
        except httpx.TimeoutException as exc:
            raise HebrahApiError(f"{error_prefix} timed out", 504) from exc
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"{error_prefix} failed: control plane unreachable",
                503,
            ) from exc
        if not response.is_success:
            raise HebrahApiError(
                f"{error_prefix} failed ({response.status_code})",
                response.status_code,
                self._client._error_detail(response.text),
            )
        return response.json()

    def metadata(self) -> dict[str, Any]:
        return self._fhir_get("/fhir/R4/metadata", error_prefix="FHIR metadata read")

    def read(
        self,
        resource_type: str,
        resource_id: str,
        *,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        res_type = safe_path_segment(resource_type, "resource_type")
        res_id = safe_path_segment(resource_id, "resource_id")
        return self._fhir_get(
            f"/fhir/R4/{res_type}/{res_id}",
            access_token=access_token,
            error_prefix=f"FHIR {res_type} read",
        )

    def search(
        self,
        resource_type: str,
        params: dict[str, str | int | bool] | None = None,
        *,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        res_type = safe_path_segment(resource_type, "resource_type")
        return self._fhir_get(
            f"/fhir/R4/{res_type}",
            access_token=access_token,
            params=params,
            error_prefix=f"FHIR {res_type} search",
        )

    def read_patient(self, patient_id: str, access_token: str | None = None) -> dict[str, Any]:
        pat_id = safe_path_segment(patient_id, "patient_id")
        return self._fhir_get(
            f"/fhir/R4/Patient/{pat_id}",
            access_token=access_token,
            error_prefix="FHIR Patient read",
        )


class _PatientsResource:
    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def list(self, *, connection_id: str | None = None) -> PatientListResponse:
        warnings.warn(
            "patients.list() is deprecated; use "
            "sandbox.list_synthetic_resources('Patient', connection_id=...).",
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
            "patients.get() is deprecated; use sandbox.resource('Patient', patient_id) "
            "for connection-scoped reads.",
            DeprecationWarning,
            stacklevel=2,
        )
        pat_id = safe_path_segment(patient_id, "patient_id")
        return self._client._request(
            "GET",
            f"/v1/patients/{pat_id}",
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
        deliv_id = safe_path_segment(delivery_id, "delivery_id")
        return self._client._request(
            "POST",
            f"/v1/webhooks/deliveries/{deliv_id}/replay",
        )


class HebrahClient:
    """Sync client for the hebrah Isolated Health Environments & control plane API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        default_connection_id: str | None = None,
        environment_id: str | None = None,
        include_error_detail: bool = True,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get("HEBRAH_API_KEY")
        self._api_key = assert_safe_token(resolved_key, "api_key")
        self._base_url = resolve_base_url(base_url)

        raw_conn = (
            default_connection_id
            if default_connection_id is not None
            else os.environ.get("HEBRAH_CONNECTION_ID")
        )
        self._default_connection_id = raw_conn.strip() if raw_conn and raw_conn.strip() else None

        raw_env = (
            environment_id
            if environment_id is not None
            else os.environ.get("HEBRAH_ENVIRONMENT_ID")
        )
        self._environment_id = raw_env.strip() if raw_env and raw_env.strip() else None

        self._include_error_detail = include_error_detail
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )
        self.environments = _EnvironmentsResource(self)
        self.db = _DbResource(self)
        self.connections = _ConnectionsResource(self)
        self.agent = _AgentResource(self)
        self.sandbox = _SandboxResource(self)
        self.patients = _PatientsResource(self)
        self.webhooks = _WebhooksResource(self)
        self.smart = _SmartResource(self)
        self.fhir = _FhirResource(self)

    @property
    def base_url(self) -> str:
        return self._base_url

    def _resolve_environment_id(self, environment_id: str | None) -> str:
        resolved = environment_id or self._environment_id
        if not resolved or not resolved.strip():
            raise ValueError(
                "environment_id is required (pass as argument or set in HebrahClient)"
            )
        return resolved.strip()

    def _resolve_connection_id(self, connection_id: str | None) -> str | None:
        return connection_id or self._default_connection_id

    def _connection_params(self, connection_id: str | None = None) -> dict[str, str] | None:
        resolved = self._resolve_connection_id(connection_id)
        return {"connection_id": resolved} if resolved else None

    def _error_detail(self, raw: str | None) -> str | None:
        return raw if self._include_error_detail else None

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> HebrahClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, str]:
        try:
            response = httpx.get(f"{self._base_url}/health", timeout=30.0)
        except httpx.TimeoutException as exc:
            raise HebrahApiError("Health check timed out", 504) from exc
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"Control plane unreachable at {self._base_url}. Is hebrah-api running?",
                503,
            ) from exc
        if not response.is_success:
            raise HebrahApiError(
                f"Health check failed ({response.status_code})",
                response.status_code,
                self._error_detail(response.text),
            )
        return response.json()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._http.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise HebrahApiError("Control plane request timed out", 504) from exc
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"Control plane unreachable at {self._base_url}. Is hebrah-api running?",
                503,
            ) from exc

        if not response.is_success:
            raise HebrahApiError(
                f"Control plane request failed ({response.status_code})",
                response.status_code,
                self._error_detail(response.text),
            )

        if not response.content:
            return None
        return response.json()
