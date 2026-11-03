
import csv
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

ARCHITECTURES = {
    "conventional": {
        "source": ROOT / "rtl" / "multiplier" / "conventional_multiplier.sv",
        "top": "conventional_multiplier",
    },
    "karatsuba": {
        "source": ROOT / "rtl" / "multiplier" / "PARAMETERIZED_MULTIPLIER.sv",
        "top": "karatsuba_multiplier",
    },
}

WIDTHS = [8, 16, 32, 64]
CSV_PATH = RESULTS / "baseline.csv"


def synthesize(architecture, config, width):
    log_path = RESULTS / f"{architecture}_N{width}_yosys.log"

    script = (
        f"read_verilog -sv {config['source']}; "
        f"hierarchy -top {config['top']} -chparam N {width}; "
        "proc; opt; techmap; opt; stat"
    )

    print(f"\nSynthesizing {architecture}, N={width}...")

    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(
            ["yosys", "-p", script],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            text=True,
        )

    report = log_path.read_text(encoding="utf-8", errors="replace")

    # Read the final total cell count from the Yosys log.
    

    matches = re.findall(
        r"^\s*(\d+)\s+cells\s*$",
        report,
        flags=re.MULTILINE,
    )

    if not matches:
        raise RuntimeError(
            f"Could not find cell count in {log_path}"
        )

    cell_count = int(matches[-1])

    print(f"  Generic logic cells: {cell_count}")

    return {
        "architecture": architecture,
        "width": width,
        "generic_logic_cells": cell_count,
        "yosys_log": str(log_path.relative_to(ROOT)),
    }


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = []

    for width in WIDTHS:
        for architecture, config in ARCHITECTURES.items():
            if not config["source"].is_file():
                raise FileNotFoundError(
                    f"RTL source not found: {config['source']}"
                )

            rows.append(synthesize(architecture, config, width))

    with CSV_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "architecture",
                "width",
                "generic_logic_cells",
                "yosys_log",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCompleted {len(rows)} synthesis runs.")
    print(f"CSV saved to: {CSV_PATH}")


if __name__ == "__main__":
    main()
