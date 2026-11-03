"""Select an isolated ADC simulator; enable PDK model pruning before source."""
from pathlib import Path
import os
import re
import shutil
import subprocess

RELATIVE_BINARY = Path("build/tools/ngspice-44.2/install/bin/ngspice")


def major_version(text):
    patterns = (r"ngspice-(\d+)", r"ngspice compiled from ngspice revision\s+(\d+)")
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match[1])
    raise ValueError("cannot identify the ADC ngspice version")


def select(root):
    override = os.environ.get("AUTOMX_ADC_NGSPICE")
    isolated = Path(root)/RELATIVE_BINARY
    candidate = override or (str(isolated) if isolated.is_file() else shutil.which("ngspice"))
    if not candidate:
        raise ValueError("run scripts/setup_flow2_adc_ngspice.py --root . --run on Ubuntu first")
    executable = shutil.which(candidate) or candidate
    executable = str(Path(executable).expanduser().resolve(strict=True))
    result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=15)
    version = result.stdout+result.stderr
    if result.returncode or major_version(version) < 36:
        raise ValueError("ADC requires ngspice >=36 with PDK model pruning; native ngspice31 is kept for core evidence. "
                         "Run python3 scripts/setup_flow2_adc_ngspice.py --root . --run")
    return executable, version.strip()


def driver():
    # Compatibility must be set BEFORE source expands the 34k-MOS PDK
    # wrappers. A set inside adc.spice's own .control would run too late.
    # -n bypasses user .spiceinit; neither HOME nor system tools are modified.
    return "\n".join(["ADC isolated runtime driver", "VKEEP driver_node 0 0", "RKEEP driver_node 0 1k",
        ".control", "set ngbehavior=hs", "set numthreads=4",
        "echo AUTOMX_ADC_RUNTIME=SOURCE_ENTER_HS", "source adc.spice",
        "echo AUTOMX_ADC_RUNTIME=SOURCE_RETURNED", "quit", ".endc", ".end", ""])


def recovery_driver(source="adc.spice", *, fast_skywater=False):
    if not re.fullmatch(r"[A-Za-z0-9_]+\.spice", source):
        raise ValueError("unsafe ADC source filename")
    # hsa does not repair the old PDK's double-quoted DW expression: that
    # syntax is corrected in a derived native TT model library before source.
    # KLU is explicitly selected: a binary compiled with KLU still defaults
    # to Sparse 1.3 unless selected. noinit suppresses printing, not DC solve.
    lines = ["ADC KLU capacitor-network recovery driver",
        "VKEEP driver_node 0 0", "RKEEP driver_node 0 1k", ".control",
        "set ngbehavior=hsa", "set num_threads=4", "option klu", "option noinit"]
    if fast_skywater:
        lines += ["set skywaterpdk"]  # four MOS terminals checked before using this profile
    return "\n".join(lines+[
        "echo AUTOMX_ADC_RUNTIME=SOURCE_ENTER_HSA_KLU", f"source {source}",
        "echo AUTOMX_ADC_RUNTIME=SOURCE_RETURNED", "quit", ".endc", ".end", ""])
