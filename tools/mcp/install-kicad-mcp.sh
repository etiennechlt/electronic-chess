#!/usr/bin/env bash
# Install the KiCad MCP server (mixelpixx/KiCAD-MCP-Server) next to the
# repository, build it and point .mcp.json at it.
#
# The server is not vendored: it is a Node + Python project of several
# hundred megabytes once built. This script clones its stable branch into
# .mcp/kicad-mcp-server (ignored by git), installs the Node and Python
# dependencies, builds the TypeScript bridge and checks that KiCad's own
# Python module (pcbnew) is importable, which the server needs.
#
# Usage:
#   tools/mcp/install-kicad-mcp.sh            # install or update
#   tools/mcp/install-kicad-mcp.sh --check    # only verify the install
#
# Prerequisites on Debian and Ubuntu: apt-get install kicad kicad-symbols
# kicad-footprints (KiCad 7.0.11 works), Node 18 or later, python3 and pip.
# KICAD_MCP_REF selects another git ref than stable (main, a tag).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="$ROOT/.mcp/kicad-mcp-server"
REF="${KICAD_MCP_REF:-stable}"
REPO="https://github.com/mixelpixx/KiCAD-MCP-Server.git"

check() {
    local ok=0
    if [ -f "$DEST/dist/index.js" ]; then
        echo "server built: $DEST/dist/index.js"
    else
        echo "server not built: $DEST/dist/index.js is missing"
        ok=1
    fi
    if python3 -c "import pcbnew" 2>/dev/null; then
        echo "pcbnew: $(python3 -c 'import pcbnew; print(pcbnew.GetBuildVersion())')"
    else
        echo "pcbnew is not importable by python3: install KiCad (apt-get install kicad)"
        ok=1
    fi
    if command -v node >/dev/null; then
        echo "node: $(node --version)"
    else
        echo "node is missing"
        ok=1
    fi
    return $ok
}

if [ "${1:-}" = "--check" ]; then
    check
    exit $?
fi

mkdir -p "$ROOT/.mcp"
if [ -d "$DEST/.git" ]; then
    echo "updating $DEST ($REF)"
    git -C "$DEST" fetch --depth 1 origin "$REF"
    git -C "$DEST" checkout -q FETCH_HEAD
else
    echo "cloning $REPO ($REF) into $DEST"
    git clone --depth 1 --branch "$REF" "$REPO" "$DEST"
fi

cd "$DEST"
npm install
npm run build
python3 -m pip install -q -r requirements.txt

check
echo
echo "Done. The server is declared in $ROOT/.mcp.json (tools/mcp/kicad-mcp.sh);"
echo "restart the Claude Code session or run /mcp to connect it."
