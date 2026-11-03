"""Fixed standard route repair excluding delay buffers from new optimization.

LibreLane 3.0.16 applies EXTRA_EXCLUDED_CELLS through its normal set_dont_use
mechanism. Existing cells and all timing models remain present. Only the
standard timing-repair step receives all nine original STA corners.
Sources: librelane/config/flow.py, steps/openroad.py and
scripts/openroad/common/io.tcl at https://github.com/librelane/librelane/tree/3.0.16
"""
from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.steps import OpenROAD

EXCLUDED_CELLS = ["sky130_fd_sc_hd__clkdlybuf*"]
CORNERS = [f"{rc}_{pvt}" for rc in ("nom", "min", "max")
           for pvt in ("tt_025C_1v80", "ss_100C_1v60", "ff_n40C_1v95")]


def validate_optimization_config(config):
    if list(config.get("EXTRA_EXCLUDED_CELLS") or []) != EXCLUDED_CELLS:
        raise ValueError("Require the fixed delay-buffer optimization exclusion")
    if list(config["STA_CORNERS"]) != CORNERS:
        raise ValueError("Require the original nine STA corners")


class NonDelayBufferDesignRepair(OpenROAD.RepairDesignPostGRT):
    def __init__(self, config, *args, **kwargs):
        validate_optimization_config(config)
        super().__init__(config, *args, **kwargs)


class AllCornerTimingPostGRT(OpenROAD.ResizerTimingPostGRT):
    def __init__(self, config, *args, **kwargs):
        validate_optimization_config(config)
        super().__init__(config.copy(RSZ_CORNERS=list(CORNERS)), *args, **kwargs)


@Flow.factory.register("HuLLCirqNpu2RouteClosureV2")
class Npu2RouteClosureV2(Classic):
    Substitutions = {"OpenROAD.RepairDesignPostGRT": NonDelayBufferDesignRepair,
                     "OpenROAD.ResizerTimingPostGRT": AllCornerTimingPostGRT}


if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
