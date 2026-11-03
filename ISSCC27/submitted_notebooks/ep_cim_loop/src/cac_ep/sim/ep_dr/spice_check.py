"""SPICE measure table (.ms0) reader used by real_circuit/infer_deck.py and infer_deck_wire.py."""
import numpy as np


def parse_ms0(path):
    """.ms0 -> {name: array of values (one per sample)}. Words before the first number are the names
    (index, .data arguments, measures, temper, alter#); the rest is one sample per len(names) numbers."""
    tok = path.read_text().split('.TITLE', 1)[1].split('\n', 1)[1].split()
    names = []
    for i, w in enumerate(tok):
        try:
            float(w); break
        except ValueError:
            names.append(w.lower())
    vals = np.array([float(x) if x != 'failed' else np.nan for x in tok[i:]]).reshape(-1, len(names))
    return {n: vals[:, j] for j, n in enumerate(names)}
