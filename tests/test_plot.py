"""The face plotter's command line: what it checks before KiCad is needed."""

from __future__ import annotations

import plot


def test_plot_rejects_an_unknown_face(tmp_path, capsys):
    rc = plot.main([str(tmp_path / "x.kicad_pcb"), "--faces", "top,side"])
    assert rc == 2
    assert "unknown face(s): side" in capsys.readouterr().out


def test_plot_faces_cover_the_two_sides_and_the_editor_view():
    assert set(plot.FACES) == {"top", "bottom", "both"}
    layers, mirrored = plot.FACES["bottom"]
    assert mirrored is True  # the board turned over, as one looks at it
    assert "B.Cu" in layers and "F.Cu" not in layers
    assert "F.Cu" in plot.FACES["both"][0] and "B.Cu" in plot.FACES["both"][0]
