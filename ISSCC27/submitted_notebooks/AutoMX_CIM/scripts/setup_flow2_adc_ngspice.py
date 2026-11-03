#!/usr/bin/env python3
"""Build a pinned, console-only ADC ngspice on Ubuntu inside this checkout.

No sudo, package-manager action, HOME configuration or system-tool replacement.
Sources: official ngspice 44.2 release; checksum also recorded by Void Linux.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts.flow2_adc_runtime import RELATIVE_BINARY

URL = "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/old-releases/44.2/ngspice-44.2.tar.gz"
SHA256 = "e7dadfb7bd5474fd22409c1e5a67acdec19f77e597df68e17c5549bc1390d7fd"


def extract(archive, destination):
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        for entry in members:
            path = PurePosixPath(entry.name)
            if (path.is_absolute() or ".." in path.parts or not path.parts
                    or path.parts[0] != "ngspice-44.2" or not (entry.isfile() or entry.isdir())):
                raise ValueError(f"unexpected release archive entry: {entry.name}")
            resolved = (Path(destination)/entry.name).resolve()
            if not resolved.is_relative_to(Path(destination).resolve()):
                raise ValueError("release path escapes build directory")
        source.extractall(destination, members=members)


def run(root, *, execute=False, jobs=4):
    root = Path(root).resolve()
    base = root/"build/tools/ngspice-44.2"
    binary = root/RELATIVE_BINARY
    report = {"format": "automx-cim-adc-ngspice-setup-v1", "status": "PREPARED",
        "version": "44.2", "url": URL, "source_sha256": SHA256,
        "binary": str(binary), "scope": "isolated ADC runtime only; no simulation or physical gate is inferred"}
    if not execute:
        return report
    if sys.platform != "linux" or not 1 <= jobs <= 32:
        raise ValueError("run on the Ubuntu EDA server with 1..32 build jobs")
    tools = ["cc", "make"]
    missing = [p for p in tools if not shutil.which(p)]
    if not (shutil.which("bison") or shutil.which("byacc") or shutil.which("yacc")):
        missing.append("bison or byacc")
    if missing:
        raise ValueError("missing server build tools: "+", ".join(missing))
    base.mkdir(parents=True, exist_ok=True)
    log = base/"setup.log"
    try:
        if not binary.is_file():
            archive = base/"ngspice-44.2.tar.gz"
            if not archive.is_file():
                print("Downloading pinned ngspice44.2 source on server", flush=True)
                with urllib.request.urlopen(URL, timeout=90) as source, archive.open("xb") as output:
                    shutil.copyfileobj(source, output)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
                raise ValueError("download checksum differs; inspect the retained archive")
            source_dir = base/"ngspice-44.2"
            if not source_dir.exists():
                extract(archive, base)
            commands = [[str(source_dir/"configure"), "--prefix="+str(base/"install"),
                "--with-x=no", "--with-readline=no", "--disable-debug", "--enable-xspice", "--enable-openmp"],
                ["make", "-j", str(jobs)], ["make", "install"]]
            with log.open("a", encoding="utf-8") as stream:
                for command in commands:
                    print("ADC runtime build: "+" ".join(command)+f"; log={log}", flush=True)
                    subprocess.run(command, cwd=source_dir, stdout=stream, stderr=subprocess.STDOUT,
                                   check=True, timeout=1800)
        result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, check=True, timeout=15)
        if "ngspice-44.2" not in result.stdout+result.stderr:
            raise ValueError("installed runtime is not the pinned version")
        report.update(status="ADC_RUNTIME_INSTALLED_NOT_MEASURED", binary_sha256=common._sha(binary),
                      version_output=(result.stdout+result.stderr).strip())
    except Exception as error:
        report.update(status="BLOCKED_ADC_RUNTIME_SETUP", error=f"{type(error).__name__}: {error}")
    finally:
        common._save(base/"setup.json", report)
        dest = root/"server_results/flow2_adc_runtime"
        dest.mkdir(parents=True, exist_ok=True)
        for path in (base/"setup.json", log):
            if path.is_file():
                shutil.copy2(path, dest/path.name)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    a = parser.parse_args()
    report = run(a.root, execute=a.run, jobs=a.jobs)
    print(json.dumps(report, indent=2))
    if a.run and report["status"] != "ADC_RUNTIME_INSTALLED_NOT_MEASURED":
        raise SystemExit(1)
