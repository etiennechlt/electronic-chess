#!/bin/sh
# Regenerate the analog board then export its fabrication files.
# Run from the repository root: sh hardware/mockup-2x2/analog-board/export.sh
# PYTHON is the interpreter that builds, KICAD_PYTHON the one that
# carries the pcbnew module (on Debian and Ubuntu /usr/bin/python3).
set -e
DIR=hardware/mockup-2x2/analog-board
PY="${PYTHON:-python3}"
KPY="${KICAD_PYTHON:-/usr/bin/python3}"
export PYTHONPATH="tools${PYTHONPATH:+:$PYTHONPATH}"
"$PY" -m analoggen build --out "$DIR" --render docs/images/analog-board.png
"$KPY" tools/gerbers.py "$DIR/analog-board.kicad_pcb"
