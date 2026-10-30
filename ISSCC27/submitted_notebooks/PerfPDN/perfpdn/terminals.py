"""Ask ngspice for the MOS terminal-current Jacobian at the saved operating point."""
from pathlib import Path
import subprocess
import json

import numpy as np


def read_scalar_raw(path):
    raw = Path(path).read_text()
    if "No. Points: 1\n" not in raw or "Flags: real\n" not in raw:
        raise ValueError(f"Expected one real operating point or transfer function: {path}")
    variables, data = raw.split("Variables:\n", 1)[1].split("Values:\n", 1)
    names = [line.split()[1].lower() for line in variables.splitlines() if line.strip()]
    values = [float(value) for value in data.split()[1:]]
    if not np.all(np.isfinite(values)):
        raise ValueError(f"Non-finite simulator values: {path}")
    return dict(zip(names, values, strict=True))


def terminal_jacobian(base, output, ports, simulator="ngspice"):
    ports = list(ports)
    original = read_scalar_raw(base / "op.raw")
    output.mkdir(parents=True, exist_ok=True)
    state = json.loads((base/"summary.json").read_text())
    deck = ["MOS terminal derivatives at the complete circuit's solved operating point"]
    deck += state["design"]["directives"] + state["device_lines"]

    for port in ports:
        deck.append(f"vc_{port} {port} 0 {original[f'v({port})']:.17g}")
    deck += [".control", "set filetype=ascii", "op", "write clamped.raw all"]
    for row in range(len(ports)):
        for col in range(len(ports)):
            deck += [f"tf i(vc_{ports[row]}) vc_{ports[col]}",
                     f"write tf_{row}_{col}.raw all"]
            (output / f"tf_{row}_{col}.raw").unlink(missing_ok=True)
    deck += [".endc", ".end"]
    (output / "clamped.raw").unlink(missing_ok=True)
    (output / "circuit.cir").write_text("\n".join(deck) + "\n")
    (output / ".spiceinit").write_text((base / ".spiceinit").read_text())
    with (output / "ngspice.log").open("w") as log:
        subprocess.run([str(simulator), "-b", "circuit.cir"], cwd=output,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    clamped = read_scalar_raw(output / "clamped.raw")

    mismatch = max(abs(-clamped[f"i(vc_{port})"] - original[f"i(v_{port})"]) for port in ports)
    jacobian = -np.array([[read_scalar_raw(output / f"tf_{r}_{c}.raw")["v(transfer_function)"]
                          for c in range(len(ports))] for r in range(len(ports))])
    row_sum = np.max(np.abs(jacobian.sum(axis=1)))
    column_sum = np.max(np.abs(jacobian.sum(axis=0)))

    if mismatch > 1e-11 or max(row_sum, column_sum) > 1e-10:
        raise ValueError(f"Terminal linearization failed: current={mismatch}, row={row_sum}, column={column_sum}")
    return jacobian, {"clamped_current_mismatch_A": mismatch,
                      "max_row_sum_S": float(row_sum), "max_column_sum_S": float(column_sum)}
