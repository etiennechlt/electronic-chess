#!/bin/sh
# Regenerate the board from config/board.yaml, then export its
# fabrication files. Run from the repository root:
#   sh hardware/mockup-2x2/coil-board/export.sh
# PYTHON is the interpreter that builds, KICAD_PYTHON the one that
# carries the pcbnew module (on Debian and Ubuntu /usr/bin/python3).
# tools/gerbers.py fills the pours, reads the layer set off the board
# and refuses a board whose routing is not closed: this board is in
# that state, see its README.
set -e
DIR=hardware/mockup-2x2/coil-board
PY="${PYTHON:-python3}"
KPY="${KICAD_PYTHON:-/usr/bin/python3}"
export PYTHONPATH="tools${PYTHONPATH:+:$PYTHONPATH}"
"$PY" -m coilgen build --out "$DIR" --render docs/images/coil-board.png
"$KPY" tools/gerbers.py "$DIR/coil-board.kicad_pcb"
