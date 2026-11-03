"""M2 calibrated pulse-rejection model (CALIBRATED_EXPLORATORY).

r_filter = a + b * (input_slew / d), fitted per (cell, output-pulse polarity)
from ngspice + SKY130A pulse sweeps (scripts/fit_m2.py).  Cells without
calibration borrow the calibration of the same logic function at another drive
strength when one exists (e.g. nor2_4 -> nor2_1, recorded in ``proxied``);
otherwise they fall back to M1 behaviour (r = 1) and are counted in ``uncalibrated``.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

# bundled copy (refreshed by scripts/fit_m2.py); repo copy lives in data/m2/
DEFAULT = Path(__file__).resolve().parent / "data" / "m2_model.json"


class M2Model:
    def __init__(self, path=DEFAULT, clamp=(0.3, 2.5)):
        """``path=None``: no calibration (every cell falls back to M1, r = 1)."""
        self.path = path
        self.cells = json.loads(Path(path).read_text())["cells"] if path else {}
        if path and Path(path) != DEFAULT and Path(path).parent.name.lower().startswith("sky130_fd_sc_hd"):
            # a SKY130 corner calibration: the trailing-slew coefficient (a fraction of the edge's own
            # slope) is taken from the typical-corner calibration where the corner has none
            tt = json.loads(DEFAULT.read_text())["cells"]
            for k, pols in self.cells.items():
                for pol, d in pols.items():
                    if "trail_alpha" not in d and "trail_alpha" in tt.get(k, {}).get(pol, {}):
                        d["trail_alpha"] = tt[k][pol]["trail_alpha"]
        self.clamp = clamp
        self.uncalibrated = {}
        self.proxied = {}

    def resolve(self, key):
        """Calibrated cell key used for ``key`` (itself, a drive-strength proxy, or None)."""
        return proxy_key(key, self.cells, self.proxied)

    @staticmethod
    def _key(c):
        name = c.library_cell or c.kind
        return name.split("__")[-1]

    def r_filter(self, c, out_pol, slew_fs, delay_fs):
        k = self.resolve(self._key(c)) or self._key(c)
        m = self.cells.get(k, {}).get(out_pol, {}).get("r_filter")
        if m is None or m["a"] != m["a"]:
            self.uncalibrated[k] = self.uncalibrated.get(k, 0) + 1
            return 1.0
        x = slew_fs / delay_fs if delay_fs > 0 else 0.0
        return min(self.clamp[1], max(self.clamp[0], m["a"] + m["b"] * x))

    __call__ = r_filter

    def trail_alpha(self, c, out_pol):
        """Trailing-edge slew coefficient alpha of (cell, output-pulse polarity); 0 if not calibrated."""
        k = self.resolve(self._key(c)) or self._key(c)
        return float(self.cells.get(k, {}).get(out_pol, {}).get("trail_alpha", 0.0))


def proxy_key(key, available, record=None):
    """``key`` if calibrated, else the same function at the nearest drive strength
    (preference _1, _0, _2, then ascending); None if the function is not calibrated."""
    if key in available:
        return key
    base = re.sub(r"_\d+$", "", key)
    cands = [x for x in available if re.sub(r"_\d+$", "", x) == base]
    if not cands:
        return None
    pref = {"1": 0, "0": 1, "2": 2}
    best = min(cands, key=lambda x: (pref.get(x.rsplit("_", 1)[-1], 3), x))
    if record is not None:
        record[key] = best
    return best


def calibration_for(library_name):
    """Bundled M2 calibration file for a Liberty library, or None.

    A library with its own calibration directory (e.g. a SKY130 corner calibrated by
    scripts/calibrate_corner.py) uses it; other SKY130 HD libraries use
    ``data/m2_model.json``; other libraries use
    ``data/<prefix>/m2_model.json`` when a calibration directory whose name the library
    name starts with exists (written by the multi-PDK calibration scripts)."""
    import os
    if os.environ.get("GS_M2_CAL"):                  # explicit override (e.g. the typical calibration at a corner)
        return Path(os.environ["GS_M2_CAL"])
    name = (library_name or "").lower()
    base = DEFAULT.parent
    for d in sorted(base.iterdir(), key=lambda p: -len(p.name)):   # most specific first (e.g. a SKY130 corner)
        if d.is_dir() and (d / "m2_model.json").exists() and name.startswith(d.name.lower()):
            return d / "m2_model.json"
    if name.startswith("sky130_fd_sc_hd"):
        return DEFAULT
    return None
