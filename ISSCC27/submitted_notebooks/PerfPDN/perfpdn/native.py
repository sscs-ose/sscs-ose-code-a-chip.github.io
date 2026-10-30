"""Run native tools and read their saved scalar and complex solutions."""
import os
import re
import subprocess
from pathlib import Path
import numpy as np
from .project import ROOT, SIMULATOR
from .terminals import read_scalar_raw


def execute(command, folder, log, timeout=240):
    with (folder/log).open("w") as stream:
        subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                       env={**os.environ, "QT_QPA_PLATFORM":"offscreen"}, check=True, timeout=timeout)


def spice(deck, folder, filename="circuit.cir"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder/filename).write_text("\n".join(deck)+"\n")
    (folder/".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
    with (folder/"ngspice.log").open("w") as log:
        subprocess.run([str(SIMULATOR), "-b", filename], cwd=folder,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240)
    text = (folder/"ngspice.log").read_text()
    if re.search(r"(?mi)^\s*(?:error\b|fatal\b)|no such vector|no data saved", text):
        raise ValueError(f"Native simulation failed: {folder/'ngspice.log'}")


def complex_raw(path):
    text = Path(path).read_text()
    if "Flags: complex\n" not in text or "No. Points: 1\n" not in text:
        raise ValueError(f"Expected one complex AC point: {path}")
    variables, data = text.split("Variables:\n", 1)[1].split("Values:\n", 1)
    names = [line.split()[1].lower() for line in variables.splitlines() if line.strip()]
    numbers = np.fromstring(" ".join(data.split()[1:]).replace(",", " "), sep=" ").reshape(-1, 2)
    result = dict(zip(names, numbers[:, 0]+1j*numbers[:, 1], strict=True))
    if not all(np.isfinite(v) for v in result.values()):
        raise ValueError(f"Non-finite AC solution: {path}")
    return result


def number(text):
    match = re.fullmatch(r"([-+\d.eE]+)(meg|[tgkmunpf])?", text.lower())
    if not match:
        raise ValueError(f"Expected a numeric SPICE value with optional SI suffix: {text}")
    scale = {None:1, "t":1e12, "g":1e9, "meg":1e6, "k":1e3,
             "m":1e-3, "u":1e-6, "n":1e-9, "p":1e-12, "f":1e-15}
    return float(match[1])*scale[match[2]]
