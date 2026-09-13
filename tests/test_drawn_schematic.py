"""The drawn quadrant schematic (analoggen.sheets, quadgen.schematic) carries
exactly the circuit, for the 4 x 4 quadrant and the reduced 2 x 2 one.

The engine's own check runs first (every pin placed, every net one
connected component, no two nets joined, every net labelled); when
kicad-cli is installed the netlist KiCad reads back from the sheets is
compared with the circuit too, local labels normalized to their bare
name (KiCad prefixes them with the sheet path)."""

import shutil
import subprocess
from pathlib import Path

import pytest
from analoggen.fplib import FOOTPRINT_DIR
from analoggen.sexp import atom, find_all, find_one, parse
from analoggen.sheets import Placed, SchematicError
from analoggen.symlib import SYMBOL_DIR, load_symbol
from quadgen.circuit import build_quadrant_circuit, cell_refs, coil_count, mux_refs
from quadgen.schematic import quadrant_schematic
from quadgen.variant import project_name, reduced_config

pytestmark = pytest.mark.skipif(
    not SYMBOL_DIR.exists() or not FOOTPRINT_DIR.exists(), reason="KiCad libraries not installed"
)


def _variants(cfg):
    return [(cfg, "quadrant"), (reduced_config(cfg), project_name(reduced_config(cfg), True))]


def test_symbol_orientation_matrix():
    """Pins of rotated and mirrored units land where KiCad draws them."""
    from analoggen.circuit import Component, Part

    sym = load_symbol("Device", "R")
    comp = Component("R1", Part("Device", "R", ""), "1k", {"1": "A", "2": "B"}, sym=sym)
    up = Placed(comp, 1, 10.0, 10.0)
    assert up.pin_pos("1") == (10.0, 6.19) and up.pin_away("1") == (0, -1)
    left = Placed(comp, 1, 10.0, 10.0, rot=90)
    assert left.pin_pos("1") == (6.19, 10.0) and left.pin_away("1") == (-1, 0)
    down = Placed(comp, 1, 10.0, 10.0, rot=180)
    assert down.pin_pos("1") == (10.0, 13.81)
    fet = load_symbol("Transistor_FET", "AO3401A")
    pins = {"1": "G", "2": "S", "3": "D"}
    q = Component("Q1", Part("Transistor_FET", "AO3401A", ""), "", pins, sym=fet)
    plain, flipped = Placed(q, 1, 0.0, 0.0), Placed(q, 1, 0.0, 0.0, mirror="x")
    assert plain.pin_pos("2")[1] > 0 > plain.pin_pos("3")[1]  # source below, drain above
    assert flipped.pin_pos("2")[1] < 0 < flipped.pin_pos("3")[1]  # source on top once mirrored


@pytest.mark.parametrize("which", ["full", "reduced"])
def test_drawing_carries_the_circuit(cfg, which):
    cfg = cfg if which == "full" else reduced_config(cfg)
    ckt, chain = build_quadrant_circuit(cfg)
    sch = quadrant_schematic(cfg, ckt, chain, project_name(cfg, which == "reduced"))
    sch.verify(ckt)  # raises SchematicError on any split, joined or unnamed net
    files = sch.emit()
    assert f"{project_name(cfg, which == 'reduced')}.kicad_sch" in files
    n = coil_count(cfg)
    assert len([f for f in files if f.startswith("cells-")]) == -(-n // 4)


def test_verification_catches_a_wrong_wire(cfg):
    """A wire joining two nets is refused before anything is written."""
    cfg = reduced_config(cfg)
    ckt, chain = build_quadrant_circuit(cfg)
    sch = quadrant_schematic(cfg, ckt, chain, "x")
    chain_sheet = next(s for s in sch.sheets if s.name == "chain")
    r25 = next(p for p in chain_sheet.placed if p.comp.ref == "R25")
    chain_sheet.wire(r25.pin_pos("1"), r25.pin_pos("2"))  # shorts OUT_STAGE to AMP_OUT
    with pytest.raises(SchematicError, match="joined"):
        sch.verify(ckt)


def test_reduced_circuit_is_the_full_one_shrunk(cfg):
    full, _ = build_quadrant_circuit(cfg)
    small, _ = build_quadrant_circuit(reduced_config(cfg))
    assert coil_count(reduced_config(cfg)) == 4
    refs = {c.ref for c in small.components}
    for k in range(1, 5):
        assert set(cell_refs(k).values()) <= refs
    assert "NT5" not in refs and "U4" not in refs and "LD9" not in refs
    assert [r for r, _f, _e in mux_refs(4)] == ["U3"]
    u1 = next(c for c in small.components if c.ref == "U1")
    assert len(u1.nc) == 12  # outputs 4 to 15 unused
    # the two design points of note 17: freewheel diode, no pull-up on the P-FET gate
    for ckt in (full, small):
        cr = cell_refs(1)
        free = next(c for c in ckt.components if c.ref == cr["free"])
        assert free.pins == {"1": "C1_A", "2": "GND"}
        assert "damp_pu" not in cr
        r7 = next(c for c in ckt.components if c.ref == "R7")
        assert r7.value == "470R"


def _netlist(path: Path) -> dict[str, set[tuple[str, str]]]:
    nets = {}
    for net in find_all(find_one(parse(path.read_text(encoding="utf-8")), "nets"), "net"):
        name = atom(find_one(net, "name")[1])
        if name.startswith("unconnected-"):
            continue
        nodes = find_all(net, "node")
        nets[name.rsplit("/", 1)[-1]] = {
            (atom(find_one(n, "ref")[1]), atom(find_one(n, "pin")[1])) for n in nodes
        }
    return nets


@pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli not installed")
@pytest.mark.parametrize("which", ["full", "reduced"])
def test_kicad_reads_the_circuit_back(cfg, which, tmp_path: Path):
    cfg = cfg if which == "full" else reduced_config(cfg)
    name = project_name(cfg, which == "reduced")
    ckt, chain = build_quadrant_circuit(cfg)
    sch = quadrant_schematic(cfg, ckt, chain, name)
    sch.verify(ckt)
    for filename, text in sch.emit().items():
        (tmp_path / filename).write_text(text, encoding="utf-8")
    out = tmp_path / "q.net"
    root = tmp_path / f"{name}.kicad_sch"
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist", "--output", str(out), str(root)],
        check=True,
        capture_output=True,
    )
    assert _netlist(out) == {net: set(nodes) for net, nodes in ckt.nets.items()}
