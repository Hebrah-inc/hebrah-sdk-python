"""HebrahAgentHarness: Agent-native MCP & Isolated Health Environments harness."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .errors import HebrahApiError
from .types import (
    DEFAULT_BASE_URL,
    DEFAULT_MCP_URL,
    assert_safe_external_url,
    assert_safe_token,
    redact_secrets,
    resolve_base_url,
    validate_timeout,
)

MAX_TOOL_OUTPUT_CHARS = 256_000
MAX_DOC_URLS = 20


class HebrahAgentHarness:
    """High-level harness for AI agents to provision isolated health environments,
    query attached databases via credential-blind handles, and invoke MCP tools.
    """

    def __init__(
        self,
        pat: str | None = None,
        *,
        mcp_url: str | None = None,
        api_base_url: str | None = None,
        integration_agent_url: str | None = None,
        dashboard_url: str | None = None,
        include_error_detail: bool = True,
        timeout: float = 60.0,
    ) -> None:
        resolved_pat = (
            pat
            if pat is not None
            else os.environ.get("HEBRAH_PAT") or os.environ.get("HEBRAH_API_KEY")
        )
        self._pat = assert_safe_token(resolved_pat, "pat")
        self.include_error_detail = include_error_detail

        raw_mcp = (
            mcp_url if mcp_url is not None else os.environ.get("HEBRAH_MCP_URL") or DEFAULT_MCP_URL
        )
        validated_mcp = resolve_base_url(raw_mcp)
        self.mcp_url = validated_mcp[:-4] if validated_mcp.endswith("/mcp") else validated_mcp
        self._mcp_endpoint = f"{self.mcp_url}/mcp"

        raw_api = (
            api_base_url
            if api_base_url is not None
            else os.environ.get("HEBRAH_BASE_URL") or DEFAULT_BASE_URL
        )
        self.api_base_url = resolve_base_url(raw_api)
        self.integration_agent_url = resolve_base_url(
            integration_agent_url
            if integration_agent_url is not None
            else os.environ.get("HEBRAH_INTEGRATION_AGENT_URL") or "http://localhost:3050"
        )
        self.dashboard_url = resolve_base_url(
            dashboard_url
            if dashboard_url is not None
            else os.environ.get("HEBRAH_DASHBOARD_URL") or "https://app.hebrah.com"
        )
        self.timeout = validate_timeout(timeout, default=60.0)
        self._http = httpx.Client(timeout=self.timeout)

    def __repr__(self) -> str:
        return (
            f"HebrahAgentHarness(mcp_url={self.mcp_url!r}, "
            f"api_base_url={self.api_base_url!r}, pat='[REDACTED]')"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def __getstate__(self) -> dict[str, Any]:
        state = dict(self.__dict__)
        state["_pat"] = "[REDACTED]"
        state.pop("_http", None)
        return state

    def close(self) -> None:
        """Close the underlying persistent HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> HebrahAgentHarness:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _headers(self, *, mcp: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._pat}",
            "Content-Type": "application/json",
        }
        if mcp:
            headers["Accept"] = "application/json, text/event-stream"
        return headers

    @staticmethod
    def _parse_mcp_response_body(response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "").lower()
        if "text/event-stream" in content_type:
            for line in response.text.splitlines():
                stripped = line.strip()
                if stripped.startswith("data:"):
                    payload_str = stripped[5:].strip()
                    if payload_str:
                        return json.loads(payload_str)
        return response.json()

    def _mcp_call(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Invoke a tool on the hosted Streamable HTTP MCP server."""
        if not tool_name or not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError("tool_name must be a non-empty string")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name.strip(),
                "arguments": arguments or {},
            },
        }
        try:
            response = self._http.post(
                self._mcp_endpoint,
                headers=self._headers(mcp=True),
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise HebrahApiError(f"MCP tool '{tool_name}' timed out", 504) from exc
        except httpx.RequestError as exc:
            raise HebrahApiError(
                f"MCP host unreachable at {self.mcp_url}",
                503,
            ) from exc

        if not response.is_success:
            raise HebrahApiError(
                f"MCP tool '{tool_name}' failed ({response.status_code})",
                response.status_code,
                redact_secrets(response.text[:MAX_TOOL_OUTPUT_CHARS]),
            )

        data = self._parse_mcp_response_body(response)
        if "error" in data and data["error"]:
            err = data["error"]
            msg = err.get("message", "MCP error") if isinstance(err, dict) else str(err)
            raise HebrahApiError(redact_secrets(msg), 400)

        result = data.get("result", data)
        if isinstance(result, dict) and result.get("isError"):
            content = result.get("content", [])
            err_text = (
                content[0].get("text", "MCP tool returned an error")
                if isinstance(content, list) and content and isinstance(content[0], dict)
                else "MCP tool returned an error"
            )
            raise HebrahApiError(redact_secrets(str(err_text)[:MAX_TOOL_OUTPUT_CHARS]), 400)

        content = result.get("content", []) if isinstance(result, dict) else []
        if content and isinstance(content, list) and isinstance(content[0], dict):
            text = content[0].get("text", "")
            if isinstance(text, str):
                bounded = text[:MAX_TOOL_OUTPUT_CHARS]
                try:
                    return json.loads(bounded)
                except (ValueError, TypeError):
                    return redact_secrets(bounded)
        return result

    # ── Isolated Health Environments MCP Tools ────────────────

    def consult_architect(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        current_blueprint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Consult the Conversational Environment Architect via MCP (`env_consult_architect`)."""
        if not prompt or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        args: dict[str, Any] = {"prompt": prompt.strip()}
        if session_id:
            args["session_id"] = session_id.strip()
        if current_blueprint is not None:
            args["current_blueprint"] = current_blueprint
        return self._mcp_call("env_consult_architect", args)

    def create_environment(
        self,
        *,
        name: str,
        archetype: str = "ambulatory_clinic",
        modules: list[str] | None = None,
        patient_count: int = 25,
        ttl_hours: int = 24,
    ) -> dict[str, Any]:
        """Provision a new isolated health environment via MCP (`env_create`)."""
        return self._mcp_call(
            "env_create",
            {
                "name": name,
                "archetype": archetype,
                "modules": modules if modules is not None else ["postgresql", "sqlite"],
                "patient_count": patient_count,
                "ttl_hours": ttl_hours,
            },
        )

    def list_environments(self) -> dict[str, Any]:
        """List active isolated health environments via MCP (`env_list`)."""
        return self._mcp_call("env_list", {})

    def get_environment(self, environment_id: str) -> dict[str, Any]:
        """Get status and attached modules for an isolated environment (`env_status`)."""
        return self._mcp_call("env_status", {"environment_id": environment_id})

    def destroy_environment(self, environment_id: str) -> dict[str, Any]:
        """Tear down an isolated health environment (`env_destroy`)."""
        return self._mcp_call("env_destroy", {"environment_id": environment_id})

    def attach_module(
        self,
        environment_id: str,
        module_type: str,
        *,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Attach a database module to an isolated environment (`env_attach_module`)."""
        args: dict[str, Any] = {
            "environment_id": environment_id,
            "module_type": module_type,
        }
        if config:
            args["config"] = config
        return self._mcp_call("env_attach_module", args)

    def db_query(
        self,
        environment_id: str,
        sql: str,
        *,
        module_type: str = "postgresql",
    ) -> dict[str, Any]:
        """Run a read-only SQL query against an environment's attached database (`env_db_query`)."""
        return self._mcp_call(
            "env_db_query",
            {
                "environment_id": environment_id,
                "sql": sql,
                "module_type": module_type,
            },
        )

    def db_vector_search(
        self,
        environment_id: str,
        query_text: str,
        *,
        collection: str = "clinical_notes",
        limit: int = 5,
    ) -> dict[str, Any]:
        """Run a semantic vector search against the Qdrant module (`env_db_vector_search`)."""
        return self._mcp_call(
            "env_db_vector_search",
            {
                "environment_id": environment_id,
                "query_text": query_text,
                "collection": collection,
                "limit": limit,
            },
        )

    def db_graph_query(
        self,
        environment_id: str,
        cypher: str,
    ) -> dict[str, Any]:
        """Run a read-only Cypher query against the Neo4j module (`env_db_graph_query`)."""
        return self._mcp_call(
            "env_db_graph_query",
            {
                "environment_id": environment_id,
                "cypher": cypher,
            },
        )

    def list_clinic_patients(self, environment_id: str) -> dict[str, Any]:
        """List synthetic patients in an isolated clinic environment (`env_ehr_patients`)."""
        return self._mcp_call("env_ehr_patients", {"environment_id": environment_id})

    def admit_patients(
        self,
        environment_id: str,
        *,
        count: int = 5,
        department: str | None = None,
        acuity: str | None = None,
    ) -> dict[str, Any]:
        """Dynamically admit new synthetic patients into an environment (`env_admit_patients`)."""
        if count < 1 or count > 100:
            raise ValueError("count must be between 1 and 100")
        args: dict[str, Any] = {
            "environment_id": environment_id,
            "count": count,
        }
        if department:
            args["department"] = department
        if acuity:
            args["acuity"] = acuity
        return self._mcp_call("env_admit_patients", args)

    def trigger_clinic_scenario(
        self,
        environment_id: str,
        scenario_type: str = "adt_a01_admit",
        *,
        patient_id: str | None = None,
    ) -> dict[str, Any]:
        """Trigger a clinical workflow or HL7 v2 scenario (`env_ehr_trigger_scenario`)."""
        args: dict[str, Any] = {
            "environment_id": environment_id,
            "scenario_type": scenario_type,
        }
        if patient_id:
            args["patient_id"] = patient_id
        return self._mcp_call("env_ehr_trigger_scenario", args)

    def open_data_catalog(self, environment_id: str) -> dict[str, Any]:
        """Retrieve the open clinical dataset catalog (`env_open_data_catalog`)."""
        return self._mcp_call("env_open_data_catalog", {"environment_id": environment_id})

    def generate_wireguard_config(
        self,
        environment_id: str,
        *,
        peer_name: str = "developer-workstation",
    ) -> dict[str, Any]:
        """Generate a WireGuard VPN tunnel config for human GUI tools (`env_vpn_config`)."""
        return self._mcp_call(
            "env_vpn_config",
            {"environment_id": environment_id, "peer_name": peer_name},
        )

    def wallet_status(self) -> dict[str, Any]:
        """Check current agent wallet balance and auto-reload status (`wallet_status`)."""
        return self._mcp_call("wallet_status", {})

    # ── Connector Catalog & EHR Modeling Helpers ──────────────

    def discover_connectors(
        self,
        *,
        pack_id: str | None = None,
        demo_only: bool = False,
    ) -> dict[str, Any]:
        """List connector packs and targets available on the platform."""
        args: dict[str, Any] = {}
        if pack_id:
            args["pack_id"] = pack_id
        if demo_only:
            args["demo_only"] = True
        return self._mcp_call("list_connector_targets", args)

    def verify_audit_chain(self, connection_id: str) -> dict[str, Any]:
        """Verify cryptographic SHA-256 hash chain for a connection's audit log."""
        return self._mcp_call("verify_audit_chain", {"connection_id": connection_id})

    def research_and_model_ehr(
        self,
        *,
        vendor_name: str | None = None,
        vendor: str | None = None,
        connection_id: str | None = None,
        doc_urls: list[str] | None = None,
        doc_text: str | None = None,
        sample_payloads: list[dict[str, Any]] | None = None,
        focus_resources: list[str] | None = None,
        apply_immediately: bool = True,
    ) -> dict[str, Any]:
        """Generate a custom EHR sandbox profile from documentation or sample payloads."""
        resolved_vendor = (vendor_name or vendor or "").strip()
        if not resolved_vendor:
            raise ValueError("vendor_name must be a non-empty string")
        if doc_urls and len(doc_urls) > MAX_DOC_URLS:
            raise ValueError(f"Maximum of {MAX_DOC_URLS} doc_urls allowed per request")
        safe_urls = [assert_safe_external_url(u, "doc_url") for u in (doc_urls or [])]
        payload: dict[str, Any] = {
            "vendor_name": resolved_vendor,
            "doc_urls": safe_urls,
            "sample_payloads": sample_payloads or [],
            "focus_resources": focus_resources
            or ["Patient", "Observation", "Condition", "Encounter"],
            "apply_immediately": apply_immediately,
        }
        if connection_id:
            payload["connection_id"] = connection_id
        if doc_text:
            payload["doc_text"] = doc_text
        try:
            response = self._http.post(
                f"{self.api_base_url}/v1/sandbox/model-ehr",
                headers=self._headers(),
                json=payload,
            )
            if response.is_success:
                return response.json()
        except httpx.RequestError:
            pass
        return self._mcp_call("model_custom_ehr", payload)

    def apply_custom_ehr_model(self, model_spec: dict[str, Any]) -> dict[str, Any]:
        """Apply a custom EHR specification JSON directly to the active sandbox."""
        try:
            response = self._http.put(
                f"{self.api_base_url}/v1/sandbox/config",
                headers=self._headers(),
                json={"ehr_Profile": "Custom", "custom_Model": model_spec},
            )
            if response.is_success:
                return response.json()
        except httpx.RequestError:
            pass
        return self._mcp_call("apply_custom_ehr_model", {"model_spec": model_spec})
