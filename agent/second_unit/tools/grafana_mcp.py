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
import shutil
import subprocess

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


def _resolve_mcp_grafana_binary() -> str:
    """Find the mcp-grafana binary. `go install` puts it in $GOPATH/bin (or
    $GOBIN), which usually isn't on PATH for subprocesses spawned outside an
    interactive shell — this is what actually bit us during the day-7
    vertical slice test, so resolve it robustly rather than assuming PATH.
    """
    override = os.environ.get("MCP_GRAFANA_BIN")
    if override:
        return override

    found = shutil.which("mcp-grafana")
    if found:
        return found

    try:
        gopath = subprocess.run(
            ["go", "env", "GOPATH"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        candidate = os.path.join(gopath, "bin", "mcp-grafana")
        if os.path.exists(candidate):
            return candidate
    except (OSError, subprocess.SubprocessError):
        pass

    raise RuntimeError(
        "mcp-grafana binary not found. Install with `go install "
        "github.com/grafana/mcp-grafana/cmd/mcp-grafana@latest`, or set "
        "MCP_GRAFANA_BIN to its absolute path."
    )

# Tool categories, matching mcp-grafana's real `-enabled-tools` flag (verified
# against `mcp-grafana --help` during the day-7 vertical slice — the tool
# GROUPS names here are its actual category names, not guessed ones. Tempo
# trace access comes through the "proxied" category (proxied MCP servers
# discovered from the stack's datasources), not a dedicated "tempo" category.
# Write access is NOT split by category on this binary — it's one global
# `-disable-write` boolean — so read_toolset() sets that flag and
# write_toolset() narrows the category list instead.
READ_TOOL_CATEGORIES = "search,dashboard,datasource,prometheus,loki,incident,proxied,annotations"
WRITE_TOOL_CATEGORIES = "annotations,incident"


def _connection_params(enable_write: bool) -> StdioConnectionParams:
    grafana_url = os.environ["GRAFANA_URL"]
    token = os.environ["GRAFANA_SERVICE_ACCOUNT_TOKEN"]

    args = ["-t", "stdio"]
    if enable_write:
        args += ["-enabled-tools", WRITE_TOOL_CATEGORIES]
    else:
        args += ["-enabled-tools", READ_TOOL_CATEGORIES, "-disable-write"]

    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=_resolve_mcp_grafana_binary(),
            args=args,
            env={
                "GRAFANA_URL": grafana_url,
                "GRAFANA_SERVICE_ACCOUNT_TOKEN": token,
            },
        ),
    )


def read_toolset() -> MCPToolset:
    """Read-only tools for evidence agents: metrics, logs, traces, dashboards.
    `-disable-write` makes this a hard guarantee, not just a category filter.
    """
    return MCPToolset(connection_params=_connection_params(enable_write=False))


def write_toolset() -> MCPToolset:
    """Write-enabled tools for the ActuatorAgent only: annotations + incidents."""
    return MCPToolset(connection_params=_connection_params(enable_write=True))
