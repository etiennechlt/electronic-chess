#!/bin/sh
# Regenerate the analog board then export fabrication files.
# Run from the repository root: sh hardware/mockup-2x2/analog-board/export.sh
set -e
DIR=hardware/mockup-2x2/analog-board
PY="${PYTHON:-python3}"
"$PY" -m analoggen build --out "$DIR" --render docs/images/analog-board.png
mkdir -p "$DIR/gerbers"
kicad-cli pcb export gerbers --output "$DIR/gerbers/" \
  --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,F.Paste,Edge.Cuts \
  "$DIR/analog-board.kicad_pcb"
kicad-cli pcb export drill --output "$DIR/gerbers/" --format excellon \
  --excellon-separate-th "$DIR/analog-board.kicad_pcb"
(cd "$DIR/gerbers" && zip -o ../analog-board-gerbers.zip ./*)
echo "Fabrication archive: $DIR/analog-board-gerbers.zip"
