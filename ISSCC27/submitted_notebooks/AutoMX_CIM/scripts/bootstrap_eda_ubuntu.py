#!/usr/bin/env python3
"""One-command Ubuntu bootstrap for AutoMX-CIM's notebook EDA stack.

This script intentionally never accepts a sudo password.  Run ``sudo -v`` in a
terminal before invoking it from Jupyter, so sudo credentials are cached.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

APT_PACKAGES = (
    "build-essential", "git", "make", "python3-venv", "python3-pip",
    "docker.io", "verilator", "ngspice", "magic", "klayout", "netgen-lvs",
)
OPENLANE_REPO = "https://github.com/The-OpenROAD-Project/OpenLane.git"


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.check_call(command, cwd=str(cwd) if cwd else None)


def need_sudo() -> list[str]:
    if os.geteuid() == 0:
        return []
    result = subprocess.run(["sudo", "-n", "true"], check=False)
    if result.returncode:
        raise RuntimeError(
            "System install needs cached sudo credentials. In a terminal run "
            "`sudo -v`, then rerun this notebook cell."
        )
    return ["sudo", "-n"]


def install_system() -> None:
    if sys.platform != "linux":
        raise RuntimeError("The automatic system installer currently supports Ubuntu/Debian Linux only.")
    sudo = need_sudo()
    run([*sudo, "apt-get", "update"])
    run([*sudo, "apt-get", "install", "-y", *APT_PACKAGES])
    # netgen-lvs is sometimes installed outside PATH on Ubuntu.
    netgen_bin = Path("/usr/lib/netgen/bin")
    if netgen_bin.is_dir() and str(netgen_bin) not in os.environ.get("PATH", "").split(":"):
        os.environ["PATH"] = f"{netgen_bin}:{os.environ.get('PATH', '')}"


def install_conda_yosys() -> None:
    conda = shutil.which("conda")
    in_conda = (Path(sys.prefix) / "conda-meta").is_dir()
    if conda and in_conda:
        run([conda, "install", "-y", "--prefix", sys.prefix, "-c", "conda-forge", "yosys"])
    elif not shutil.which("yosys"):
        sudo = need_sudo()
        run([*sudo, "apt-get", "install", "-y", "yosys"])
    else:
        print("Using existing Yosys:", shutil.which("yosys"))


def docker_ready() -> bool:
    return shutil.which("docker") is not None and subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    ).returncode == 0


def install_openlane(destination: Path) -> None:
    if not docker_ready():
        user = os.environ.get("USER", "<user>")
        raise RuntimeError(
            "Docker is installed but unavailable to this login. Run "
            f"`sudo usermod -aG docker {user}`, log out/in, run `sudo -v`, then rerun this cell."
        )
    if not (destination / ".git").is_dir():
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", OPENLANE_REPO, str(destination)])
    # OpenLane v1's supported Docker bootstrap downloads its pinned image/PDK.
    run(["make"], cwd=destination)
    run(["make", "test"], cwd=destination)
    os.environ["OPENLANE_ROOT"] = str(destination)
    print("OPENLANE_ROOT=", destination)


def verify() -> None:
    for tool, args in {
        "verilator": ["--version"], "yosys": ["-V"], "ngspice": ["--version"],
        "magic": ["-version"], "klayout": ["-v"], "netgen": ["-batch"],
    }.items():
        path = shutil.which(tool) or ("/usr/lib/netgen/bin/netgen" if tool == "netgen" and Path("/usr/lib/netgen/bin/netgen").exists() else None)
        if not path:
            print(f"{tool:10}: MISSING")
            continue
        result = subprocess.run([path, *args], capture_output=True, text=True, check=False)
        first = (result.stdout or result.stderr).splitlines()
        print(f"{tool:10}: {path} :: {first[0] if first else 'found'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", action="store_true", help="install Ubuntu/Debian EDA packages")
    parser.add_argument("--openlane", action="store_true", help="clone and verify OpenLane v1 Docker flow")
    parser.add_argument("--openlane-root", type=Path, default=Path.home() / ".cache" / "automx-cim" / "OpenLane")
    args = parser.parse_args()
    if args.system:
        install_system()
        install_conda_yosys()
    if args.openlane:
        install_openlane(args.openlane_root)
    verify()


if __name__ == "__main__":
    main()