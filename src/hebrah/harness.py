from __future__ import annotations

import json
from typing import Any

import httpx


class HebrahAgentHarness:
    """Thin orchestration layer: MCP tools + integration-agent for BYOM EHR modeling."""

    def __init__(
        self,
        *,
        mcp_url: str,
        pat: str,
        integration_agent_url: str = "http://localhost:3050",
    ) -> None:
        self.mcp_url = mcp_url.rstrip("/")
        self.pat = pat
        self.integration_agent_url = integration_agent_url.rstrip("/")

    def _mcp_call(self, tool: str, args: dict[str, Any] | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args or {}},
        }
        with httpx.Client(timeout=60.0) as client:
            res = client.post(
                f"{self.mcp_url}/mcp",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.pat}",
                },
                json=payload,
            )
            res.raise_for_status()
            body = res.json()
        if body.get("error"):
            raise RuntimeError(body["error"].get("message", "MCP tool error"))
        content = (body.get("result") or {}).get("content") or []
        if content and content[0].get("text"):
            return json.loads(content[0]["text"])
        return body.get("result")

    def get_developer_doc(self, connection_id: str | None = None) -> Any:
        return self._mcp_call(
            "get_connection_developer_doc",
            {"connectionId": connection_id} if connection_id else {},
        )

    def get_synthetic_ehr_profile(self, connection_id: str | None = None) -> Any:
        return self._mcp_call(
            "get_synthetic_ehr_profile",
            {"connectionId": connection_id} if connection_id else {},
        )

    def list_base_ehr_models(self) -> Any:
        return self._mcp_call("list_ehr_base_models")

    def research_and_model_ehr(
        self,
        *,
        vendor: str,
        connection_id: str,
        doc_urls: list[str] | None = None,
        doc_text: str | None = None,
    ) -> Any:
        chunk_ids: list[str] = []
        with httpx.Client(timeout=60.0) as client:
            for url in doc_urls or []:
                res = client.post(
                    f"{self.integration_agent_url}/v1/ingest",
                    json={"connection_id": connection_id, "url": url},
                )
                if res.is_success:
                    chunk_ids.append(res.json()["chunk_id"])
            if doc_text:
                res = client.post(
                    f"{self.integration_agent_url}/v1/ingest",
                    json={"connection_id": connection_id, "text": doc_text},
                )
                if res.is_success:
                    chunk_ids.append(res.json()["chunk_id"])
            gen = client.post(
                f"{self.integration_agent_url}/v1/generate",
                json={
                    "connection_id": connection_id,
                    "vendor": vendor,
                    "doc_chunk_ids": chunk_ids,
                },
            )
            gen.raise_for_status()
            return gen.json()

    def validate_sandbox(self, connection_id: str | None = None) -> dict[str, Any]:
        profile = self.get_synthetic_ehr_profile(connection_id)
        doc = self.get_developer_doc(connection_id)
        return {"profile": profile, "doc": doc, "ok": bool(profile and doc)}

    def apply_custom_ehr_model(
        self,
        *,
        connection_id: str,
        model_pack: dict[str, Any],
        dashboard_url: str = "http://localhost:3000",
        confirm_token: str | None = None,
    ) -> Any:
        token = confirm_token or f"confirm_{connection_id}"
        with httpx.Client(timeout=60.0) as client:
            res = client.post(
                f"{dashboard_url.rstrip('/')}/api/connections/{connection_id}/byom/apply",
                headers={
                    "Authorization": f"Bearer {self.pat}",
                    "Content-Type": "application/json",
                },
                json={"modelPack": model_pack, "confirmToken": token},
            )
            if not res.is_success:
                raise RuntimeError(
                    f"BYOM apply failed ({res.status_code}): {res.text}"
                )
            return res.json()
