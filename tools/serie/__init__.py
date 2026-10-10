"""Tools for the project films: the signature sound and the facts they show.

The series bible (docs/serie) gives each piece its note: its resonance
line from chessboard_calc, transposed into the audible. The films only
ever show numbers computed here from config/board.yaml, never typed by
hand into a composition.

    python -m serie signature OUT_DIR       # one .wav per note, plus the scale
    python -m serie film media/pitch/ecoute # facts, sounds and renders of a film
"""
