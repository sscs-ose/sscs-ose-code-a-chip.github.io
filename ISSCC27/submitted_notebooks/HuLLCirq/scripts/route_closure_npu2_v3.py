"""One standard electrical repair after the retained all-corner timing repair.

No custom Tcl or netlist rewriting is used. The new unique step runs the
unmodified LibreLane 3.0.16 RepairDesignPostGRT implementation, then the standard
MidSTA, detailed-route, extraction and final all-nine-corner STA stages.
Sources: librelane/flows/{classic,sequential}.py and steps/openroad.py at
https://github.com/librelane/librelane/tree/3.0.16
"""
from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.steps import OpenROAD

EXCLUDED_CELLS = ["sky130_fd_sc_hd__clkdlybuf*"]
CORNERS = [f"{rc}_{pvt}" for rc in ("nom", "min", "max")
           for pvt in ("tt_025C_1v80", "ss_100C_1v60", "ff_n40C_1v95")]
FINAL_REPAIR_STEP = "HuLLCirq.RepairDesignAfterTimingV3"


def validate_optimization_config(config):
    if list(config.get("EXTRA_EXCLUDED_CELLS") or []) != EXCLUDED_CELLS:
        raise ValueError("Retain the fixed delay-buffer optimization exclusion")
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


class ElectricalRepairAfterTiming(NonDelayBufferDesignRepair):
    id = FINAL_REPAIR_STEP
    name = "Standard Electrical Repair After Timing (NPU2 V3)"


@Flow.factory.register("HuLLCirqNpu2RouteClosureV3")
class Npu2RouteClosureV3(Classic):
    Substitutions = {
        "OpenROAD.RepairDesignPostGRT": NonDelayBufferDesignRepair,
        "OpenROAD.ResizerTimingPostGRT": AllCornerTimingPostGRT,
        "+OpenROAD.ResizerTimingPostGRT": ElectricalRepairAfterTiming,
    }


if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
