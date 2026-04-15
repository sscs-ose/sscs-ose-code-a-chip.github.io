"""DLL closed-loop simulator.

    CLKin ──> PD ──> Controller ──> DCDL ──> CLKout
               ^                               |
               └───────────────────────────────┘

Each module owns its own timing:
    - PD returns (up, down, valid_time)
    - Controller pipelines ctrl internally via configure_pipeline()
    - DCDL delay shifts CLKout relative to CLKin
"""

from __future__ import annotations

from .phase_detector import PhaseDetector
from .controller import Controller
from .dcdl import DCDL


def simulate(
    pd: PhaseDetector,
    controller: Controller,
    dcdl: DCDL,
    clk_period_ps: float = 5000.0,
    num_cycles: int = 200,
) -> dict:
    """Run a DLL closed-loop simulation.

    Returns dict of lists (one entry per cycle):
        clk_in, clk_out, up, down, ctrl, dcdl_delay, phase_error

    phase_error is reported explicitly as:
        clk_out_edge - clk_in_edge
    so the loop target is phase_error -> 0.
    """
    controller.reset()
    controller.configure_pipeline(pd.prop_delay_ps, clk_period_ps)

    t = dict(
        clk_in=[], clk_out=[],
        up=[], down=[],
        ctrl=[], dcdl_delay=[], phase_error=[],
    )

    prev_delay = dcdl.delay(controller.ctrl)

    for cycle in range(num_cycles):
        clk_in_edge = cycle * clk_period_ps
        clk_out_edge = (cycle - 1) * clk_period_ps + prev_delay

        up, down, _ = pd.detect(clk_out_edge, clk_in_edge)
        controller.update(up, down)
        current_delay = dcdl.delay(controller.ctrl)
        phase_error = clk_out_edge - clk_in_edge

        t["clk_in"].append(clk_in_edge)
        t["clk_out"].append(clk_out_edge)
        t["up"].append(up)
        t["down"].append(down)
        t["ctrl"].append(controller.ctrl)
        t["dcdl_delay"].append(current_delay)
        t["phase_error"].append(phase_error)

        prev_delay = current_delay

    return t
