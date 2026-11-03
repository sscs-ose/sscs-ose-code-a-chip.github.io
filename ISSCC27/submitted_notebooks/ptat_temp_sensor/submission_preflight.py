#!/usr/bin/env python3
"""Code-a-Chip submission preflight for this project directory."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "PTAT_Temperature_Sensor_Code_a_Chip.ipynb"
CELL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
PINNED_PDK = "12df12e2e74145e31c5a13de02f9a1e176b56e67"


def run(name, *cmd):
    p = subprocess.run(list(cmd), cwd=ROOT, text=True, capture_output=True)
    if p.returncode:
        print(f"[FAIL] {name}\n{p.stdout}\n{p.stderr}")
        return False
    print(f"[PASS] {name}")
    return True


def check_notebook() -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"cannot parse notebook: {exc}"]

    cells = nb.get("cells", [])
    if nb.get("nbformat") != 4:
        errors.append("nbformat must be 4")
    if len(cells) < 8:
        errors.append("notebook must contain at least 8 cells")
    if not any(c.get("cell_type") == "code" for c in cells):
        errors.append("notebook must contain executable code")

    ids = [c.get("id") for c in cells]
    if any(not isinstance(x, str) or not CELL_ID_RE.fullmatch(x) for x in ids):
        errors.append("every notebook cell must have a valid stable id")
    if len(set(ids)) != len(ids):
        errors.append("notebook cell ids must be unique")

    markdown = "\n".join(
        "".join(c.get("source", []))
        if isinstance(c.get("source"), list)
        else str(c.get("source", ""))
        for c in cells
        if c.get("cell_type") == "markdown"
    )
    required_markers = {
        "submission contact": "Submission contact",
        "team member": "Team member",
        "references": "## References",
        "official Colab badge": "colab-badge.svg",
        "official upstream badge target": "github/sscs-ose/sscs-ose-code-a-chip.github.io",
        "retained ngspice version": "ngspice 46",
        "pinned SKY130/open_pdks revision": PINNED_PDK,
        "reproducibility section": "## Reproducibility",
        "limitations section": "## Limitations",
        "innovation section": "## Innovation and contribution",
    }
    for label, marker in required_markers.items():
        if marker not in markdown:
            errors.append(f"missing {label}: {marker!r}")

    all_source = "\n".join(
        "".join(c.get("source", []))
        if isinstance(c.get("source"), list)
        else str(c.get("source", ""))
        for c in cells
    )
    executable_markers = {
        "Colab supporting-files bootstrap": (
            "sscs-ose-code-a-chip.github.io.git"
        ),
        "Colab bootstrap subprocess": "subprocess.run",
    }
    for label, marker in executable_markers.items():
        if marker not in all_source:
            errors.append(f"missing {label}: {marker!r}")

    return not errors, errors


def main():
    ok = True
    required = [
        "README.md",
        "LICENSE",
        "design_requirements.json",
        "release_requirements.json",
        "evidence_audit.py",
        "full_pdk_evidence_audit.py",
        "pdk_calibration_analysis.py",
        "readout_budget.py",
        "seed_policy.py",
        "long_mirror_candidate.json",
        "long_mirror_evidence_audit.py",
    ]
    for name in required:
        hit = (ROOT / name).is_file()
        print(("[PASS] " if hit else "[FAIL] ") + name)
        ok &= hit

    notebook_ok, notebook_errors = check_notebook()
    print(("[PASS] " if notebook_ok else "[FAIL] ") + "Jupyter notebook submission structure")
    for error in notebook_errors:
        print("       -", error)
    ok &= notebook_ok

    ok &= run("retained evidence audit", sys.executable, "evidence_audit.py")
    ok &= run(
        "retained full-PDK evidence audit",
        sys.executable,
        "full_pdk_evidence_audit.py",
    )
    ok &= run(
        "retained calibration audit",
        sys.executable,
        "pdk_calibration_analysis.py",
        "--check",
    )
    ok &= run("behavioral readout audit", sys.executable, "readout_budget.py", "--check")
    ok &= run("long-mirror candidate evidence audit", sys.executable,
              "long_mirror_evidence_audit.py")
    print("SUBMISSION PREFLIGHT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
