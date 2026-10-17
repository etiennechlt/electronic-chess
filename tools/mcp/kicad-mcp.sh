#!/usr/bin/env bash
# Launcher of the KiCad MCP server for .mcp.json: resolves the install
# made by install-kicad-mcp.sh relative to this script, so the project
# works from any checkout path, and exposes KiCad's Python to the server.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SERVER="$ROOT/.mcp/kicad-mcp-server/dist/index.js"
if [ ! -f "$SERVER" ]; then
    echo "KiCad MCP server not installed: run tools/mcp/install-kicad-mcp.sh" >&2
    exit 1
fi
export NODE_ENV="${NODE_ENV:-production}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
export KICAD_AUTO_LAUNCH="${KICAD_AUTO_LAUNCH:-false}"
# Debian and Ubuntu put pcbnew on the system interpreter's path already;
# the entries below cover a KiCad installed from its own packages.
export PYTHONPATH="${PYTHONPATH:-}:/usr/share/kicad/scripting/plugins:/usr/lib/kicad/lib/python3/dist-packages"
exec node "$SERVER"
