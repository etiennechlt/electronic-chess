"""The generated schematics carry exactly the nets of their circuits.

The emitter draws every pin with a stub and a global label, so the
connectivity KiCad reads back from the sheet must be the Circuit and
nothing else: a label of one group landing on a stub of another would
merge two nets silently (the quadrant once had GND and 5VA joined that
way). Checked with kicad-cli on every generated board."""

import shutil
import subprocess
from pathlib import Path

import pytest
from analoggen.fplib import FOOTPRINT_DIR
from analoggen.schematic import emit_schematic
from analoggen.sexp import atom, find_all, find_one, parse

pytestmark = pytest.mark.skipif(
    not FOOTPRINT_DIR.exists() or shutil.which("kicad-cli") is None,
    reason="KiCad libraries and kicad-cli required",
)

BOARDS = ["quadrant", "brain", "power", "motion", "clock", "analog-board"]


def _circuit(cfg, name):
    if name == "quadrant":
        from quadgen.circuit import build_quadrant_circuit, schematic_groups

        ckt, _chain = build_quadrant_circuit(cfg)
        return ckt, schematic_groups(cfg)
    if name == "analog-board":
        from analoggen.circuit import build_circuit

        ckt, _chain = build_circuit(cfg)
        return ckt, None
    import importlib

    mod = importlib.import_module(f"boardgen.{name}")
    return getattr(mod, f"build_{name}_circuit")(cfg), mod.schematic_groups()


def netlist_nets(path: Path) -> dict[str, set[tuple[str, str]]]:
    """Net name -> {(ref, pin)} of a kicad-cli netlist, unconnected pins left out."""
    nets = {}
    for net in find_all(find_first(parse(path.read_text(encoding="utf-8")), "nets"), "net"):
        name = atom(find_one(net, "name")[1])
        if name.startswith("unconnected-"):
            continue
        nets[name] = {
            (atom(find_one(n, "ref")[1]), atom(find_one(n, "pin")[1]))
            for n in find_all(net, "node")
        }
    return nets


def find_first(node, tag):
    return find_one(node, tag)


@pytest.mark.parametrize("name", BOARDS)
def test_schematic_netlist_is_the_circuit(cfg, name, tmp_path: Path):
    ckt, groups = _circuit(cfg, name)
    sch = tmp_path / f"{name}.kicad_sch"
    sch.write_text(
        emit_schematic(ckt, name, groups=groups, project=name, paper="A0", portrait=True),
        encoding="utf-8",
    )
    out = tmp_path / f"{name}.net"
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist", "--output", str(out), str(sch)],
        check=True,
        capture_output=True,
    )
    got = netlist_nets(out)
    expected = {net: set(nodes) for net, nodes in ckt.nets.items()}
    assert got == expected
