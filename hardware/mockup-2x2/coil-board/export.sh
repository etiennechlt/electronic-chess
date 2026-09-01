#!/bin/sh
# Regenerate the board from config/board.yaml, then export fabrication
# files with kicad-cli (KiCad 7+). Run from the repository root:
#   sh hardware/mockup-2x2/coil-board/export.sh
set -e
DIR=hardware/mockup-2x2/coil-board
PY="${PYTHON:-python3}"
export PYTHONPATH="tools${PYTHONPATH:+:$PYTHONPATH}"
"$PY" -m coilgen build --out "$DIR" --render docs/images/coil-board.png
mkdir -p "$DIR/gerbers"
kicad-cli pcb export gerbers --output "$DIR/gerbers/" \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  "$DIR/coil-board.kicad_pcb"
kicad-cli pcb export drill --output "$DIR/gerbers/" --format excellon \
  --excellon-separate-th "$DIR/coil-board.kicad_pcb"
(cd "$DIR/gerbers" && zip -o ../coil-board-gerbers.zip ./*)
echo "Fabrication archive: $DIR/coil-board-gerbers.zip"
