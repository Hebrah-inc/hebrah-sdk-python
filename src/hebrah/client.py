"""Synchronous HTTP client for the hebrah Isolated Health Environments & control plane API."""

from __future__ import annotations

import os
import warnings
from collections.abc import Sequence
from typing import Any

import httpx

from .errors import HebrahApiError
from .types import (
    AccessMode,
    AdmitPatientsResponse,
    AgentAccountUsage,
    AgentLedgerResponse,
    AgentRegisterResponse,
    AgentTopupResponse,
    AgentUsageSummary,
    AgentWalletStatus,
    AgentWalletSummary,
    AuditChainVerification,
    AuditVerifyResponse,
    ConnectAgentToEnvironmentResponse,
    ConnectionActionResponse,
    ConnectionListResponse,
    ConnectionQueryResponse,
    ConnectionRecord,
    ConnectionScenarioResponse,
    ConnectionScopeDict,
    ConnectionTargetsResponse,
    ConnectorPackSummary,
    ConnectorTargetSummary,
    ConsultArchitectResponse,
    ConsultStudioMessage,
    ConsultStudioResponse,
    CustodyModel,
    DbGraphQueryResponse,
    DbQueryResponse,
    DbSchemaResponse,
    DbTableSchema,
    DbVectorSearchResponse,
    EhrSummaryResponse,
    EnvironmentAutosaveState,
    EnvironmentClinicPatient,
    EnvironmentDetail,
    EnvironmentLogItem,
    EnvironmentModuleRecord,
    EnvironmentSummary,
    ExecuteOperationResponse,
    Hl7MessageRecord,
    OpenDataCatalogResponse,
    PatientListResponse,
    PayerRules,
    RecordOutcomeResponse,
    RegisterWebhookResponse,
    RevokeConnectionResponse,
    RunScenarioResponse,
    SandboxCatalog,
    SandboxConfig,
    SandboxDomainSummary,
    SandboxMetrics,
    SandboxResourceListResponse,
    ScopedConnection,
    TriggerClinicScenarioResponse,
    TriggerMockEventResponse,
    WebhookEndpoint,
    WireguardConfigResponse,
    WireGuardPeerConfigResponse,
    assert_safe_external_url,
    assert_safe_token,
    interpolate_sql_params,
    redact_secrets,
    resolve_base_url,
    safe_path_segment,
    validate_timeout,
)


class _EnvironmentsResource:
    """Provision and manage Isolated Health Environments (clinics, hospitals, modules, VPN)."""

    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def consult_architect(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        current_blueprint: dict[str, Any] | None = None,
    ) -> ConsultArchitectResponse:
        """Design or refine an isolated clinical environment blueprint interactively."""
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if len(prompt) > 8000:
            raise ValueError("prompt must be 8000 characters or fewer")
        cleaned = prompt.strip()
        body: dict[str, Any] = {"message": cleaned, "prompt": cleaned}
        if session_id:
            body["session_id"] = session_id.strip()
        if current_blueprint is not None:
            body["current_blueprint"] = current_blueprint
        data = self._client._request("POST", "/v1/environments/architect", json=body)
        if isinstance(data, dict):
            if "scope_status" in data and "scope_decision" not in data:
                data["scope_decision"] = data["scope_status"]
            elif "scope_decision" in data and "scope_status" not in data:
                data["scope_status"] = data["scope_decision"]
        return data

    def list(self, *, status: str | None = None) -> list[EnvironmentSummary]:
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        data = self._client._request("GET", "/v1/environments", params=params or None)
        if isinstance(data, dict) and "environments" in data:
            return data["environments"]
        return data

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
        seed_patients: int | None = None,
        bed_count: int = 40,
        addons: list[str] | None = None,
        archetype: str | None = None,
        modules: list[str] | None = None,
        ttl_hours: int | None = None,
        seed: int | None = None,
        custom_blueprint: dict[str, Any] | None = None,
    ) -> EnvironmentSummary:
        if not name or not name.strip():
            raise ValueError("environment name must be a non-empty string")
        resolved_patient_count = seed_patients if seed_patients is not None else patient_count
        if resolved_patient_count < 1 or resolved_patient_count > 10_000:
            raise ValueError("patient_count must be between 1 and 10000")
        body: dict[str, Any] = {
            "name": name,
            "clinic_type": archetype if archetype is not None else clinic_type,
            "patient_cohort": patient_cohort,
            "patient_count": resolved_patient_count,
            "bed_count": bed_count,
            "addons": (
                addons
                if addons is not None
                else (modules if modules is not None else ["postgres"])
            ),
        }
        if archetype is not None:
            body["archetype"] = archetype
        if seed_patients is not None:
            body["seed_patients"] = seed_patients
        if modules is not None:
            body["modules"] = modules
        if ttl_hours is not None:
            if ttl_hours < 1 or ttl_hours > 8760:
                raise ValueError("ttl_hours must be between 1 and 8760")
            body["ttl_hours"] = ttl_hours
        if seed is not None:
            body["seed"] = seed
        if custom_blueprint is not None:
            body["custom_blueprint"] = custom_blueprint
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

    def attach_module(
        self,
        module_type: str,
        *,
        environment_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> EnvironmentModuleRecord:
        return self.add_module(
            module_type,
            environment_id=environment_id,
            config=config,
        )  # type: ignore[return-value]

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

    def generate_wireguard_config(
        self,
        *,
        peer_name: str = "developer-workstation",
        environment_id: str | None = None,
    ) -> WireGuardPeerConfigResponse:
        """Generate a WireGuard VPN tunnel config for human GUI database clients."""
        if not peer_name or not peer_name.strip():
            raise ValueError("peer_name must be a non-empty string")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/vpn/peers",
            json={"peer_name": peer_name.strip()},
        )

    def export_vpn_peer(
        self,
        environment_id: str | None = None,
        *,
        peer_name: str = "developer-workstation",
    ) -> WireGuardPeerConfigResponse:
        """Alias for generate_wireguard_config."""
        return self.generate_wireguard_config(
            peer_name=peer_name,
            environment_id=environment_id,
        )

    def get_ehr_summary(self, environment_id: str | None = None) -> EhrSummaryResponse:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("GET", f"/v1/environments/{env_id}/ehr/summary")

    def ehr_summary(self, environment_id: str | None = None) -> EhrSummaryResponse:
        return self.get_ehr_summary(environment_id)

    def list_patients(
        self,
        environment_id: str | None = None,
        *,
        department: str | None = None,
        acuity: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[EnvironmentClinicPatient]:
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        params: dict[str, str] = {}
        if department:
            params["department"] = department
        if acuity:
            params["acuity"] = acuity
        if status:
            params["status"] = status
        if search:
            params["search"] = search
        if limit is not None:
            if limit < 1 or limit > 1000:
                raise ValueError("limit must be between 1 and 1000")
            params["limit"] = str(limit)
        data = self._client._request(
            "GET",
            f"/v1/environments/{env_id}/ehr/patients",
            params=params or None,
        )
        if isinstance(data, dict) and "patients" in data:
            return data["patients"]
        return data

    def admit_patients(
        self,
        *,
        count: int = 5,
        department: str | None = None,
        acuity: str | None = None,
        environment_id: str | None = None,
    ) -> AdmitPatientsResponse:
        """Dynamically generate and admit new synthetic patients into the environment."""
        if count < 1 or count > 100:
            raise ValueError("count must be between 1 and 100")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {"count": count}
        if department:
            body["department"] = department
        if acuity:
            body["acuity"] = acuity
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/ehr/patients/generate",
            json=body,
        )

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
        scenario: str = "adt_a01_admit",
        *,
        environment_id: str | None = None,
        patient_id: str | None = None,
        notes: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> TriggerClinicScenarioResponse:
        if not scenario or not scenario.strip():
            raise ValueError("scenario must be a non-empty string")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {"scenario": scenario}
        if patient_id:
            body["patient_id"] = patient_id
        if notes:
            body["notes"] = notes
        if parameters:
            body["parameters"] = parameters
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/ehr/scenarios/trigger",
            json=body,
        )

    def consult_studio(
        self,
        message: str | None = None,
        *,
        prompt: str | None = None,
        environment_id: str | None = None,
        session_id: str | None = None,
        history: list[ConsultStudioMessage] | None = None,
        apply_changes: bool = False,
    ) -> ConsultStudioResponse:
        """Interact with the live Environment AI Studio to modify or inspect an environment."""
        resolved_msg = message if message is not None else prompt
        if not resolved_msg or not isinstance(resolved_msg, str) or not resolved_msg.strip():
            raise ValueError("message must be a non-empty string")
        if len(resolved_msg) > 8000:
            raise ValueError("message must be 8000 characters or fewer")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        cleaned = resolved_msg.strip()
        body: dict[str, Any] = {
            "message": cleaned,
            "prompt": cleaned,
            "apply_changes": apply_changes,
        }
        if session_id:
            body["session_id"] = session_id.strip()
        if history is not None:
            body["history"] = history
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/studio/chat",
            json=body,
        )

    def open_data_catalog(
        self,
        environment_id: str | None = None,
    ) -> OpenDataCatalogResponse:
        """Retrieve the open clinical dataset catalog and research packs for an environment."""
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("GET", f"/v1/environments/{env_id}/open-data/catalog")

    def connect_agent(
        self,
        *,
        agent_name: str = "sdk-agent",
        scopes: list[str] | None = None,
        environment_id: str | None = None,
    ) -> ConnectAgentToEnvironmentResponse:
        """Bind an AI agent session to the environment and issue a credential-blind handle."""
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name must be a non-empty string")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {"agent_name": agent_name.strip()}
        if scopes is not None:
            body["scopes"] = scopes
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/agents/connect",
            json=body,
        )

    def get_autosave(
        self,
        environment_id: str | None = None,
    ) -> EnvironmentAutosaveState:
        """Get the current autosave snapshot state for an environment."""
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request("GET", f"/v1/environments/{env_id}/autosave")

    def update_autosave(
        self,
        state: dict[str, Any],
        *,
        enabled: bool = True,
        environment_id: str | None = None,
    ) -> EnvironmentAutosaveState:
        """Update the autosave snapshot state for an environment."""
        if not isinstance(state, dict):
            raise ValueError("state must be a dictionary")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request(
            "PUT",
            f"/v1/environments/{env_id}/autosave",
            json={"enabled": enabled, "state": state},
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
    """Credential-blind database access (`client.db.query`, `vector_search`, `graph_query`)."""

    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def query(
        self,
        sql: str,
        *,
        addon: str = "postgres",
        actor_type: str = "agent",
        environment_id: str | None = None,
        params: Sequence[Any] | None = None,
        interpolate: bool = False,
    ) -> DbQueryResponse:
        """Execute a read-only SQL query against an attached PostgreSQL or SQLite module."""
        if interpolate or (params is not None and "?" in sql):
            validated_sql = interpolate_sql_params(sql, params)
        else:
            # Still validate SQL non-emptiness and length via interpolate_sql_params
            validated_sql = interpolate_sql_params(sql, None)
            if params is not None:
                # Validate params types and null-byte safety without requiring `?` placeholders
                placeholders = ", ".join("?" for _ in params)
                if placeholders:
                    interpolate_sql_params(f"SELECT {placeholders}", params)

        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {
            "sql": validated_sql if interpolate else sql,
            "addon": addon,
            "actor_type": actor_type,
        }
        if params is not None and not interpolate:
            body["params"] = list(params)
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

    def vector_search(
        self,
        query_text: str,
        *,
        collection: str = "all",
        limit: int = 5,
        top_k: int | None = None,
        environment_id: str | None = None,
    ) -> DbVectorSearchResponse:
        """Execute a semantic vector search against the environment's Qdrant module."""
        if not query_text or not query_text.strip():
            raise ValueError("query_text must be a non-empty string")
        resolved_limit = top_k if top_k is not None else limit
        if resolved_limit < 1 or resolved_limit > 100:
            raise ValueError("limit must be between 1 and 100")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/vector/search",
            json={
                "query": query_text,
                "query_text": query_text,
                "corpus": collection,
                "collection": collection,
                "limit": resolved_limit,
            },
        )

    def graph_query(
        self,
        cypher: str,
        *,
        parameters: dict[str, Any] | None = None,
        concept_filter: str | None = None,
        limit: int = 25,
        environment_id: str | None = None,
    ) -> DbGraphQueryResponse:
        """Execute a read-only Cypher query against the environment's Neo4j Graph DB module."""
        if not cypher or not cypher.strip():
            raise ValueError("cypher must be a non-empty string")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {"cypher": cypher, "limit": limit}
        if concept_filter:
            body["concept_filter"] = concept_filter
        if parameters:
            body["parameters"] = parameters
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/graph/cypher",
            json=body,
        )

    def record_outcome(
        self,
        outcome_type: str,
        *,
        details: dict[str, Any] | None = None,
        patient_id: str | None = None,
        environment_id: str | None = None,
    ) -> RecordOutcomeResponse:
        """Record a clinical or agent evaluation outcome in the environment's database."""
        if not outcome_type or not outcome_type.strip():
            raise ValueError("outcome_type must be a non-empty string")
        env_id = safe_path_segment(
            self._client._resolve_environment_id(environment_id),
            "environment_id",
        )
        body: dict[str, Any] = {"outcome_type": outcome_type.strip()}
        if details is not None:
            body["details"] = details
        if patient_id:
            body["patient_id"] = patient_id
        return self._client._request(
            "POST",
            f"/v1/environments/{env_id}/db/outcomes",
            json=body,
        )


class _ConnectionsResource:
    """Zero-trust connector catalog, scoped connections, queries, actions, HL7 v2 & audit."""

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

    def list_packs(self, *, include_all: bool = False) -> list[ConnectorPackSummary]:
        params = {"all": "true"} if include_all else None
        data = self._client._request("GET", "/v1/connectors/packs", params=params)
        return data.get("packs", data) if isinstance(data, dict) else data

    def list_targets(
        self,
        *,
        pack_id: str | None = None,
        demo_only: bool = False,
        include_all: bool = False,
    ) -> list[ConnectorTargetSummary]:
        params: dict[str, str] = {}
        if pack_id:
            params["pack_id"] = pack_id
        if demo_only:
            params["demo_only"] = "true"
        if include_all:
            params["all"] = "true"
        data = self._client._request(
            "GET",
            "/v1/connectors/targets",
            params=params or None,
        )
        return data.get("targets", data) if isinstance(data, dict) else data

    def get_target(self, target_id: str) -> ConnectorTargetSummary:
        tid = safe_path_segment(target_id, "target_id")
        return self._client._request("GET", f"/v1/connectors/targets/{tid}")

    def list(
        self,
        *,
        include_revoked: bool = False,
        pack_id: str | None = None,
        status: str | None = None,
    ) -> ConnectionListResponse:
        params: dict[str, str] = {}
        if include_revoked:
            params["include_revoked"] = "true"
        if pack_id:
            params["pack_id"] = pack_id
        if status:
            params["status"] = status
        return self._client._request("GET", "/v1/connections", params=params or None)

    def get(self, connection_id: str | None = None) -> ScopedConnection:
        conn_id = self._require_connection_id(connection_id)
        return self._client._request("GET", f"/v1/connections/{conn_id}")

    def create(
        self,
        target: str | None = None,
        *,
        target_id: str | None = None,
        name: str | None = None,
        scopes: list[str] | None = None,
        mode: str = "demo",
        purpose: str | None = None,
        display_name: str | None = None,
        agent_id: str | None = None,
        credentials: dict[str, Any] | None = None,
        relay_id: str | None = None,
        custody_model: CustodyModel | None = None,
        access_mode: AccessMode | None = None,
        allowed_tables: list[str] | None = None,
        denied_columns: list[str] | None = None,
        max_rows: int | None = None,
        require_dlp: bool | None = None,
        baa_acknowledged: bool | None = None,
    ) -> ScopedConnection | ConnectionRecord:
        resolved_target = target or target_id
        if not resolved_target:
            raise ValueError("target is required")
        body: dict[str, Any] = {
            "target": resolved_target,
            "scopes": scopes or [],
            "mode": mode,
        }
        if name is not None:
            body["name"] = name.strip()
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
        if custody_model is not None:
            body["custody_model"] = custody_model
        if baa_acknowledged is not None:
            body["baa_acknowledged"] = baa_acknowledged
        if any(
            v is not None
            for v in (access_mode, allowed_tables, denied_columns, max_rows, require_dlp)
        ):
            scope: ConnectionScopeDict = {}
            if access_mode is not None:
                scope["access_mode"] = access_mode
            if allowed_tables is not None:
                scope["allowed_tables"] = allowed_tables
            if denied_columns is not None:
                scope["denied_columns"] = denied_columns
            if max_rows is not None:
                scope["max_rows"] = max_rows
            if require_dlp is not None:
                scope["require_dlp"] = require_dlp
            body["scope"] = scope
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

    def query(
        self,
        query: str,
        *,
        connection_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> ConnectionQueryResponse:
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        cid = self._require_connection_id(connection_id)
        body: dict[str, Any] = {"query": query}
        if parameters:
            body["parameters"] = parameters
        return self._client._request("POST", f"/v1/connections/{cid}/query", json=body)

    def execute_action(
        self,
        action_type: str,
        payload: dict[str, Any],
        *,
        connection_id: str | None = None,
    ) -> ConnectionActionResponse:
        if not action_type or not action_type.strip():
            raise ValueError("action_type must be a non-empty string")
        cid = self._require_connection_id(connection_id)
        return self._client._request(
            "POST",
            f"/v1/connections/{cid}/actions",
            json={"action_type": action_type.strip(), "payload": payload},
        )

    def trigger_scenario(
        self,
        scenario_type: str,
        *,
        connection_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> ConnectionScenarioResponse:
        if not scenario_type or not scenario_type.strip():
            raise ValueError("scenario_type must be a non-empty string")
        cid = self._require_connection_id(connection_id)
        body: dict[str, Any] = {"scenario_type": scenario_type.strip()}
        if parameters:
            body["parameters"] = parameters
        return self._client._request("POST", f"/v1/connections/{cid}/scenarios", json=body)

    def emit_hl7(
        self,
        *,
        event_type: str = "ADT^A01",
        patient_id: str | None = None,
        raw_hl7: str | None = None,
        connection_id: str | None = None,
    ) -> Hl7MessageRecord:
        cid = self._require_connection_id(connection_id)
        body: dict[str, Any] = {"event_type": event_type}
        if patient_id:
            body["patient_id"] = patient_id
        if raw_hl7:
            body["raw_hl7"] = raw_hl7
        return self._client._request("POST", f"/v1/connections/{cid}/hl7/emit", json=body)

    def list_hl7_messages(
        self,
        *,
        connection_id: str | None = None,
        limit: int = 50,
    ) -> list[Hl7MessageRecord]:
        cid = self._require_connection_id(connection_id)
        data = self._client._request(
            "GET",
            f"/v1/connections/{cid}/hl7/messages",
            params={"limit": str(limit)},
        )
        return data.get("messages", data) if isinstance(data, dict) else data

    def audit_verify(self, connection_id: str | None = None) -> AuditVerifyResponse:
        conn_id = self._require_connection_id(connection_id)
        return self._client._request("GET", f"/v1/connections/{conn_id}/audit/verify")

    def verify_audit(self, connection_id: str | None = None) -> AuditChainVerification:
        return self.audit_verify(connection_id)  # type: ignore[return-value]

    def list_audit_events(
        self,
        *,
        connection_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        cid = self._require_connection_id(connection_id)
        data = self._client._request(
            "GET",
            f"/v1/connections/{cid}/audit",
            params={"limit": str(limit)},
        )
        return data.get("events", data) if isinstance(data, dict) else data

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
    """Agent account status, usage metering, and wallet lifecycle."""

    def __init__(self, client: HebrahClient) -> None:
        self._client = client

    def wallet(self) -> AgentWalletSummary:
        return self._client._request("GET", "/v1/agent/wallet")

    def wallet_status(self) -> AgentWalletStatus:
        return self._client._request("GET", "/v1/agent/wallet")

    def usage(self) -> AgentUsageSummary | AgentAccountUsage:
        return self._client._request("GET", "/v1/agent/usage")

    def ledger(self, limit: int | None = None) -> AgentLedgerResponse:
        params = {"limit": str(limit)} if limit is not None else None
        return self._client._request("GET", "/v1/agent/ledger", params=params)

    def account(self) -> dict[str, Any]:
        """Get full agent account details and claim status."""
        return self._client._request("GET", "/v1/agent/account")

    def topup(
        self,
        amount_cents: int,
        *,
        use_saved_payment_method: bool = True,
    ) -> AgentTopupResponse:
        """Top up the organization wallet (1-click saved card or Stripe Checkout session)."""
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
            raise ValueError("amount_cents must be an integer between 100 and 1000000")
        if amount_cents < 100 or amount_cents > 1_000_000:
            raise ValueError("amount_cents must be between 100 ($1.00) and 1000000 ($10,000.00)")
        return self._client._request(
            "POST",
            "/v1/agent/topup",
            json={
                "amount_cents": amount_cents,
                "use_saved_payment_method": use_saved_payment_method,
            },
        )

    def configure_auto_reload(
        self,
        *,
        enabled: bool,
        threshold_cents: int = 200,
        reload_amount_cents: int = 1000,
    ) -> dict[str, Any]:
        """Configure wallet auto-reload threshold and top-up amount."""
        if threshold_cents < 0 or reload_amount_cents < 100:
            raise ValueError("threshold_cents must be >= 0 and reload_amount_cents >= 100")
        return self._client._request(
            "POST",
            "/v1/agent/wallet/auto-reload",
            json={
                "enabled": enabled,
                "threshold_cents": threshold_cents,
                "reload_amount_cents": reload_amount_cents,
            },
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

    def list_domains(self) -> list[SandboxDomainSummary]:
        return self.domains()

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
        raw_message: str,
        connection_id: str | None = None,
        event: str | None = None,
        deliver: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"raw_message": raw_message}
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

    def metrics(self, *, connection_id: str | None = None) -> SandboxMetrics:
        return self._client._request(
            "GET",
            "/v1/sandbox/metrics",
            params=self._client._connection_params(connection_id),
        )

    def get_config(self, *, connection_id: str | None = None) -> SandboxConfig:
        return self._client._request(
            "GET",
            "/v1/sandbox/config",
            params=self._client._connection_params(connection_id),
        )

    def update_config(
        self,
        config: SandboxConfig | dict[str, Any],
        *,
        connection_id: str | None = None,
    ) -> SandboxConfig:
        return self._client._request(
            "PUT",
            "/v1/sandbox/config",
            params=self._client._connection_params(connection_id),
            json=dict(config),
        )

    def reset(
        self,
        *,
        seed: int | None = None,
        connection_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if seed is not None:
            body["seed"] = seed
        resolved = self._client._resolve_connection_id(connection_id)
        if resolved:
            body["connection_id"] = resolved
        return self._client._request("POST", "/v1/sandbox/reset", json=body)


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
            response = self._client._http.post(
                "/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "code_verifier": code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
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
            response = self._client._http.get(
                path,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/fhir+json",
                },
                params=str_params,
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

    def read_resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self.read(resource_type, resource_id, access_token=access_token)

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

    def list(self) -> list[WebhookEndpoint]:
        return self._client._request("GET", "/v1/webhooks")

    def register(
        self,
        *,
        url: str,
        events: str = "ADT^A01, FHIR Instant",
    ) -> RegisterWebhookResponse:
        safe_url = assert_safe_external_url(url, "webhook url")
        return self._client._request(
            "POST",
            "/v1/webhooks",
            json={"url": safe_url, "events": events},
        )

    def delete(self, endpoint_id: int) -> dict[str, Any]:
        eid = safe_path_segment(str(endpoint_id), "endpoint_id")
        return self._client._request("DELETE", f"/v1/webhooks/{eid}")

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
        timeout: float = 30.0,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get("HEBRAH_API_KEY")
        self._api_key = assert_safe_token(resolved_key, "api_key")
        self._base_url = resolve_base_url(base_url)
        self._timeout = validate_timeout(timeout)

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
            timeout=self._timeout,
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

    @staticmethod
    def register_agent(
        *,
        agent_name: str,
        owner_email: str | None = None,
        purpose: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> AgentRegisterResponse:
        """Self-register a headless AI agent and receive $5.00 in free credit plus a claim URL."""
        if not agent_name or not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError("agent_name must be a non-empty string")
        clean_name = agent_name.strip()
        if len(clean_name) < 2:
            raise ValueError("agent_name must be at least 2 characters")
        if len(clean_name) > 120:
            raise ValueError("agent_name must be 120 characters or fewer")
        resolved_url = resolve_base_url(base_url)
        valid_timeout = validate_timeout(timeout)
        body: dict[str, Any] = {
            "orgName": clean_name[:80],
            "agentName": clean_name[:60],
            "agent_name": clean_name,
            "headless": True,
        }
        if owner_email and owner_email.strip():
            email = owner_email.strip()
            if any(ord(ch) < 0x20 or ord(ch) == 0x7F or ch.isspace() for ch in email):
                raise ValueError("owner_email contains invalid characters")
            body["inviteEmail"] = email
            body["owner_email"] = email
            body["headless"] = False
        if purpose and purpose.strip():
            body["purpose"] = purpose.strip()

        try:
            with httpx.Client(timeout=valid_timeout) as http:
                response = http.post(
                    f"{resolved_url}/v1/agent/account",
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise HebrahApiError("Agent registration timed out", 504) from exc
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"Control plane unreachable at {resolved_url}. Is hebrah-api running?",
                503,
            ) from exc

        if not response.is_success:
            raise HebrahApiError(
                f"Agent registration failed ({response.status_code})",
                response.status_code,
                redact_secrets(response.text),
            )
        data = response.json()
        if isinstance(data, dict):
            data.setdefault("organization_id", data.get("orgId", ""))
            data.setdefault("agent_name", data.get("orgName", clean_name))
            data.setdefault("api_key", data.get("apiKey", ""))
            data.setdefault("claim_url", data.get("claimUrl"))
            data.setdefault("free_credit_cents", 500)
        return data

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
        if not self._include_error_detail or raw is None:
            return None
        return redact_secrets(raw)

    def __repr__(self) -> str:
        return f"HebrahClient(base_url={self._base_url!r}, api_key='[REDACTED]')"

    def __str__(self) -> str:
        return self.__repr__()

    def __getstate__(self) -> dict[str, Any]:
        state = dict(self.__dict__)
        state["_api_key"] = "[REDACTED]"
        state.pop("_http", None)
        return state

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> HebrahClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, str]:
        return self._request(
            "GET",
            "/health",
            skip_auth=True,
            error_prefix="Health check",
            timeout_message="Health check timed out",
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        skip_auth: bool = False,
        error_prefix: str = "Control plane request",
        timeout_message: str = "Control plane request timed out",
    ) -> Any:
        headers: dict[str, str] = {}
        if not skip_auth:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = self._http.request(
                method,
                path,
                params=params,
                json=json,
                headers=headers or None,
            )
        except httpx.TimeoutException as exc:
            raise HebrahApiError(timeout_message, 504) from exc
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"Control plane unreachable at {self._base_url}. Is hebrah-api running?",
                503,
            ) from exc

        if not response.is_success:
            raise HebrahApiError(
                f"{error_prefix} failed ({response.status_code})",
                response.status_code,
                self._error_detail(response.text),
            )

        if not response.content:
            return None
        return response.json()
