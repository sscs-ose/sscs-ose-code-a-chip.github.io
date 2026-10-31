"""Stage-0 environment discovery and reproducibility receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any

from .config import Sky130MHAConfig
from .openlane import locate_openlane_flow


_TOOLS: dict[str, tuple[str, ...] | None] = {
    "ngspice": ("--version",),
    "magic": ("-version",),
    "klayout": ("-v",),
    "netgen": ("-batch",),
    "verilator": ("--version",),
    "yosys": ("-V",),
    # This is the legacy OpenLane v1 entry point.  It is normally under
    # $OPENLANE_ROOT, rather than in PATH, and is not invoked for a version.
    "flow.tcl": None,
}


def _locate_tool(name: str) -> str | None:
    """Find PATH tools plus the standard locations for LVS/OpenLane v1."""
    if name == "flow.tcl":
        return locate_openlane_flow()
    direct = shutil.which(name)
    if direct:
        return direct
    if name == "netgen":
        candidate = Path("/usr/lib/netgen/bin/netgen")
        if candidate.is_file():
            return str(candidate)
    return None


def _short_command_output(command: list[str]) -> tuple[int | None, str | None]:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    text = (completed.stdout or completed.stderr).strip().splitlines()
    return completed.returncode, text[0] if text else None


def _git_revision(root: Path) -> str | None:
    code, output = _short_command_output(["git", "-C", str(root), "rev-parse", "HEAD"])
    return output if code == 0 else None


def capture_environment(config: Sky130MHAConfig, root: str | Path = ".") -> dict[str, Any]:
    """Capture only observable tool/PDK state; missing tools remain explicit."""
    root_path = Path(root).resolve()
    tools: dict[str, dict[str, Any]] = {}
    for name, args in _TOOLS.items():
        executable = _locate_tool(name)
        entry: dict[str, Any] = {"path": executable, "available": executable is not None}
        if executable is not None and args is not None:
            code, version = _short_command_output([executable, *args])
            entry.update({"version_command_returncode": code, "version": version})
        tools[name] = entry
    pdk_root = os.environ.get("PDK_ROOT")
    pdk_path = (Path(pdk_root) / config.pdk) if pdk_root else None
    if pdk_path is not None and not pdk_path.exists():
        pdk_path = Path(pdk_root)
    return {
        "format": "automx-cim-environment-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root_path),
        "git_revision": _git_revision(root_path),
        "config": config.to_mapping(),
        "config_sha256": config.sha256,
        "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        "host": {"platform": platform.platform(), "machine": platform.machine()},
        "pdk": {
            "name": config.pdk,
            "PDK": os.environ.get("PDK"),
            "PDK_ROOT": pdk_root,
            "pdk_root_exists": bool(pdk_root and Path(pdk_root).is_dir()),
            "resolved_path": str(pdk_path) if pdk_path else None,
            "git_revision": _git_revision(pdk_path) if pdk_path and pdk_path.is_dir() else None,
        },
        "tools": tools,
    }


def write_environment_receipt(receipt: dict[str, Any], path: str | Path) -> dict[str, Any]:
    """Write a canonical receipt and return it with a content hash."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    destination.write_text(body, encoding="utf-8")
    return {**receipt, "receipt_sha256": sha256(body.encode("utf-8")).hexdigest()}
