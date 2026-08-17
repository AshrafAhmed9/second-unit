"""THE PARTNER INTEGRATION — Grafana MCP, called at runtime.

Runs the official open-source `grafana/mcp-grafana` server as a stdio subprocess,
authenticated against a real Grafana Cloud stack with a service-account token.
This is a deliberate choice over the hosted `mcp.grafana.com` endpoint, which
requires an interactive OAuth 2.1 browser flow that a headless Cloud Run agent
cannot complete. See second-unit/README.md "Grafana MCP transport" for the
day-3 compliance note and the OAuth fallback path.

Required environment (see infra/README.md for how these are provisioned):
  GRAFANA_URL                    e.g. https://yourstack.grafana.net
  GRAFANA_SERVICE_ACCOUNT_TOKEN  a service account token with Editor role
                                  (Editor is required for the write-back tools:
                                  annotations, incidents, activity notes)
"""
from __future__ import annotations

import os

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Tool groups exposed by grafana/mcp-grafana. We scope each evidence agent to
# only the group it needs — least privilege, and it keeps each agent's tool
# list small enough that the LLM picks correctly every time.
READ_TOOL_GROUPS = "search,dashboard,datasource,prometheus,loki,tempo,incident"
WRITE_TOOL_GROUPS = "annotations,incident"


def _connection_params(enable_write: bool) -> StdioConnectionParams:
    grafana_url = os.environ["GRAFANA_URL"]
    token = os.environ["GRAFANA_SERVICE_ACCOUNT_TOKEN"]
    groups = f"{READ_TOOL_GROUPS},{WRITE_TOOL_GROUPS}" if enable_write else READ_TOOL_GROUPS

    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command="mcp-grafana",
            args=["--tools", groups],
            env={
                "GRAFANA_URL": grafana_url,
                "GRAFANA_SERVICE_ACCOUNT_TOKEN": token,
                # mcp-grafana defaults to disabling write tools; this is the
                # documented override — keep it OFF for evidence agents.
                "GRAFANA_ENABLE_WRITE_TOOLS": "true" if enable_write else "false",
            },
        ),
    )


def read_toolset() -> MCPToolset:
    """Read-only tools for evidence agents: metrics, logs, traces, dashboards."""
    return MCPToolset(connection_params=_connection_params(enable_write=False))


def write_toolset() -> MCPToolset:
    """Write-enabled tools for the ActuatorAgent only: annotations + incidents."""
    return MCPToolset(connection_params=_connection_params(enable_write=True))
