"""Standalone diagnostic script for NandDCDL behavior.

This script prints the path taken through the NAND DCDL stages and the
observed total delay for each control word.

Run from the simulator directory:
    python3 test_nand_dcdl_behavior.py

Or from the project root:
    python3 CaC_Spring26/simulator/test_nand_dcdl_behavior.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator import NandDCDL
else:
    from . import NandDCDL


def delayed_stages(ctrl: int, num_cells: int) -> list[int]:
    """Stages that currently contribute delay in the simulator model."""
    return [i for i in range(num_cells) if not (ctrl & (1 << i))]


def stage_delay(stage: int, first_cell_delay_ps: float, remaining_cell_delay_ps: float) -> float:
    return first_cell_delay_ps if stage == 0 else remaining_cell_delay_ps


def path_summary(
    ctrl: int,
    num_cells: int,
    first_cell_delay_ps: float,
    remaining_cell_delay_ps: float,
) -> tuple[str, str]:
    """Return a readable stage-by-stage path and running delay totals."""
    stage_parts = []
    totals = []
    running_total = 0.0

    for stage in range(num_cells):
        if ctrl & (1 << stage):
            stage_parts.append(f"s{stage}:BYP")
        else:
            added = stage_delay(stage, first_cell_delay_ps, remaining_cell_delay_ps)
            running_total += added
            stage_parts.append(f"s{stage}:ADD({added:.2f})")
        totals.append(f"{running_total:.2f}")

    return " | ".join(stage_parts), " -> ".join(totals)


def format_ctrl(ctrl: int, num_cells: int) -> str:
    width = max(1, num_cells)
    return f"{ctrl:0{width}b}"


def run_diagnostic(
    num_cells: int,
    first_cell_delay_ps: float,
    remaining_cell_delay_ps: float,
    max_words: int | None,
) -> None:
    dcdl = NandDCDL(
        num_cells=num_cells,
        first_cell_delay_ps=first_cell_delay_ps,
        remaining_cell_delay_ps=remaining_cell_delay_ps,
    )

    total_words = 1 << num_cells
    if max_words is not None:
        total_words = min(total_words, max_words)

    print("NandDCDL behavior diagnostic")
    print(
        f"num_cells={num_cells}, first_cell_delay_ps={first_cell_delay_ps}, "
        f"remaining_cell_delay_ps={remaining_cell_delay_ps}"
    )
    print()
    print("Legend: BYP = bypass stage, ADD(x) = stage contributes x ps")
    print()

    for ctrl in range(total_words):
        current = dcdl.delay(ctrl)
        path, totals = path_summary(
            ctrl,
            num_cells=num_cells,
            first_cell_delay_ps=first_cell_delay_ps,
            remaining_cell_delay_ps=remaining_cell_delay_ps,
        )
        contributing = delayed_stages(ctrl, num_cells)
        print(
            f"ctrl={format_ctrl(ctrl, num_cells)} "
            f"(0x{ctrl:0{max(1, (num_cells + 3) // 4)}x})\n"
            f"  delayed stages : {contributing}\n"
            f"  stage path     : {path}\n"
            f"  running totals : {totals}\n"
            f"  observed total : {current:.2f} ps\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect NandDCDL behavior.")
    parser.add_argument("--num-cells", type=int, default=4)
    parser.add_argument("--first-cell-delay-ps", type=float, default=106.67)
    parser.add_argument("--remaining-cell-delay-ps", type=float, default=72.68)
    parser.add_argument(
        "--max-words",
        type=int,
        default=None,
        help="Limit how many control words are printed. Default prints all 2^N words.",
    )
    args = parser.parse_args()

    run_diagnostic(
        num_cells=args.num_cells,
        first_cell_delay_ps=args.first_cell_delay_ps,
        remaining_cell_delay_ps=args.remaining_cell_delay_ps,
        max_words=args.max_words,
    )


if __name__ == "__main__":
    main()
