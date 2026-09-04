"""Shared GUI configuration and simulation helpers for the DLL simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator import (
        EdgeLevelPhaseDetector,
        FilteredController,
        InverterCondDCDL,
        InverterDCDL,
        InverterGlitchFreeDCDL,
        LockedController,
        NandDCDL,
        PFDPhaseDetector,
        SaturateController,
        SingleFlipFlopPhaseDetector,
        VariableStepController,
    )
else:
    from . import (
        EdgeLevelPhaseDetector,
        FilteredController,
        InverterCondDCDL,
        InverterDCDL,
        InverterGlitchFreeDCDL,
        LockedController,
        NandDCDL,
        PFDPhaseDetector,
        SaturateController,
        SingleFlipFlopPhaseDetector,
        VariableStepController,
    )


@dataclass(frozen=True)
class TraceEntry:
    cycle: int
    clk_in: float
    clk_out: float
    up: int
    down: int
    valid_time_ps: float
    ctrl_idx: int
    ctrl_word: str
    cell_delay_ps: float
    phase_error_ps: float
    lead_state: str


class IndexedNandDCDL:
    """Map scalar controller output to prefix-clear NAND DCDL words."""

    def __init__(self, inner: NandDCDL):
        self.inner = inner
        self.num_cells = inner.num_cells
        self.full_mask = (1 << self.num_cells) - 1

    def ctrl_word(self, ctrl_index: int) -> int:
        active_stages = max(0, min(ctrl_index, self.num_cells))
        if active_stages == 0:
            return self.full_mask
        return self.full_mask ^ ((1 << active_stages) - 1)

    def delay(self, ctrl_index: int) -> float:
        return self.inner.delay(self.ctrl_word(ctrl_index))


class BinaryTapDCDLAdapter:
    """Use the controller output directly as the DCDL control/tap."""

    def __init__(self, inner):
        self.inner = inner
        self.num_cells = inner.num_cells

    def ctrl_word(self, ctrl_index: int) -> int:
        return max(0, min(ctrl_index, self.num_cells - 1))

    def delay(self, ctrl_index: int) -> float:
        return self.inner.delay(self.ctrl_word(ctrl_index))


class StageCountDCDLAdapter:
    """Treat controller output as enabled-stage count with cumulative cell delay."""

    def __init__(self, inner):
        self.inner = inner
        self.num_cells = inner.num_cells

    def ctrl_word(self, ctrl_index: int) -> int:
        return max(0, min(ctrl_index, self.num_cells))

    def delay(self, ctrl_index: int) -> float:
        active_stages = self.ctrl_word(ctrl_index)
        return self.inner._cells_delay(active_stages)


PHASE_DETECTORS = {
    "FF1": SingleFlipFlopPhaseDetector,
    "EdgeLevel": EdgeLevelPhaseDetector,
    "PFD": PFDPhaseDetector,
}

CONTROLLERS = {
    "Saturate": lambda bits, init: SaturateController(ctrl_bits=bits, init_ctrl=init),
    "Filtered": lambda bits, init: FilteredController(ctrl_bits=bits, init_ctrl=init, filter_len=3),
    "Locked": lambda bits, init: LockedController(
        ctrl_bits=bits,
        init_ctrl=init,
        acquire_step=2,
        track_step=1,
        quiet_cycles=4,
    ),
    "VariableStep": lambda bits, init: VariableStepController(
        ctrl_bits=bits,
        init_ctrl=init,
        big_step=2,
        med_step=1,
        big_thresh=4,
        med_thresh=2,
    ),
}

DCDLS = {
    "NandDCDL": {
        "factory": lambda: IndexedNandDCDL(
            NandDCDL(
                num_cells=64,
                first_cell_delay_ps=106.67,
                remaining_cell_delay_ps=73.76,
        )),
        "ctrl_bits": 6,
        "default_init_ctrl": 50,
        "default_clk_period_ps": 3013.87,
    },
    "InverterDCDL": {
        "factory": lambda: StageCountDCDLAdapter(
            InverterDCDL(
                num_cells=64,
                first_cell_delay_ps=549.12,
                remaining_cell_delay_ps=69.67,
                mux_delay_ps=0,
            )
        ),
        "ctrl_bits": 6,
        "default_init_ctrl": 50,
        "default_clk_period_ps": 3013.87,
    },
    "InverterGlitchFreeDCDL": {
        "factory": lambda: StageCountDCDLAdapter(
            InverterGlitchFreeDCDL(
                num_cells=64,
                first_cell_delay_ps=383.69,
                remaining_cell_delay_ps=75.6,
                nand_delay_ps=0,
            )
        ),
        "ctrl_bits": 6,
        "default_init_ctrl": 50,
        "default_clk_period_ps": 3013.87,
    },
}

DISPLAY_COLUMNS = ["cycle", "clk_in", "clk_out", "up", "down", "phase_error_ps"]


def run_closed_loop_simulation(
    phase_detector_name: str,
    controller_name: str,
    dcdl_name: str,
    clk_period_ps: float,
    init_ctrl: int,
    num_cycles: int,
    clk_in_start: float,
    clk_out_start: float | None,
) -> list[TraceEntry]:
    pd = PHASE_DETECTORS[phase_detector_name]()
    dcdl = DCDLS[dcdl_name]["factory"]()
    controller = CONTROLLERS[controller_name](DCDLS[dcdl_name]["ctrl_bits"], init_ctrl)

    controller.reset()
    controller.configure_pipeline(pd.prop_delay_ps, clk_period_ps)

    prev_delay_ps = dcdl.delay(controller.ctrl)
    if clk_out_start is None:
        clk_out = clk_period_ps - prev_delay_ps
    else:
        clk_out = clk_out_start
    trace: list[TraceEntry] = []

    for cycle in range(num_cycles):
        clk_in = clk_in_start + cycle * clk_period_ps

        up, down, valid_time_ps = pd.detect(clk_out, clk_in)
        controller.update(up, down)

        ctrl_idx = controller.ctrl
        ctrl_word = dcdl.ctrl_word(ctrl_idx)
        current_delay_ps = dcdl.delay(ctrl_idx)
        phase_error_ps = clk_out - clk_in
        eps = 1e-9
        if abs(phase_error_ps) <= eps:
            phase_error_ps = 0.0
            lead_state = "aligned"
        elif clk_in > clk_out:
            lead_state = "clk_in_gt_clk_out"
        else:
            lead_state = "clk_out_gt_clk_in"

        trace.append(
            TraceEntry(
                cycle=cycle,
                clk_in=round(clk_in, 2),
                clk_out=round(clk_out, 2),
                up=up,
                down=down,
                valid_time_ps=round(valid_time_ps, 2),
                ctrl_idx=ctrl_idx,
                ctrl_word=hex(ctrl_word),
                cell_delay_ps=round(current_delay_ps, 2),
                phase_error_ps=round(phase_error_ps, 2),
                lead_state=lead_state,
            )
        )

        delay_delta_ps = current_delay_ps - prev_delay_ps
        clk_out = clk_out + clk_period_ps + delay_delta_ps
        prev_delay_ps = current_delay_ps

    return trace


def trace_rows(trace: list[TraceEntry]) -> list[dict]:
    """Return the reduced table view used by the GUIs."""
    return [{key: asdict(entry)[key] for key in DISPLAY_COLUMNS} for entry in trace]


def default_init_ctrl_for_dcdl(dcdl_name: str) -> int:
    """Return the GUI/testbench default init code for a DCDL choice."""
    return int(DCDLS[dcdl_name]["default_init_ctrl"])


def trace_summary_lines(trace: list[TraceEntry]) -> tuple[str, str]:
    """Return the shared start/end summary strings used by the GUIs."""
    first = trace[0]
    last = trace[-1]
    start = f"Start: clk_out={first.clk_out:.2f} ps, phase_err={first.phase_error_ps:.2f} ps"
    end = f"End: clk_out={last.clk_out:.2f} ps, phase_err={last.phase_error_ps:.2f} ps"
    return start, end
