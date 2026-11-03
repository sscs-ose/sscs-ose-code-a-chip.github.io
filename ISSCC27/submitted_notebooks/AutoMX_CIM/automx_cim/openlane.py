"""Consistent discovery of the OpenLane 1 entry point across notebook cells."""

from __future__ import annotations

import os
from pathlib import Path
import shutil


def locate_openlane_flow() -> str | None:
    """Find an executable flow.tcl; discovery alone does not prove runtime readiness.

    The explicit override is authoritative, even if invalid. Otherwise prefer
    PATH, then OPENLANE_ROOT set by the server bootstrap cell.
    """
    override = os.environ.get("OPENLANE_FLOW_TCL")
    if override:
        candidate = Path(override).expanduser().resolve()
        return str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None
    direct = shutil.which("flow.tcl")
    if direct:
        return direct
    openlane_root = os.environ.get("OPENLANE_ROOT")
    if openlane_root:
        candidate = (Path(openlane_root).expanduser() / "flow.tcl").resolve()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
