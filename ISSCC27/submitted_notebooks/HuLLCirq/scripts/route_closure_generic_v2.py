"""Fresh standard Classic flow with bounded post-GRT electrical closure.

No checkpoints, custom Tcl, RTL changes or relaxed signoff constraints are
used. Only standard LibreLane 3.0.16 steps are selected: slow-corner electrical
repair, all-nine-corner timing repair, one further standard electrical repair,
then normal detailed routing, extraction and all-nine-corner final STA.
"""
from decimal import Decimal

from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.steps import OpenROAD


EXCLUDED_CELLS = ["sky130_fd_sc_hd__clkdlybuf*"]
CORNERS = [f"{rc}_{pvt}" for rc in ("nom", "min", "max")
           for pvt in ("tt_025C_1v80", "ss_100C_1v60", "ff_n40C_1v95")]
FINAL_REPAIR_STEP = "HuLLCirq.GenericRepairDesignAfterTimingV2"


def validate_optimization_config(config):
    if list(config.get("EXTRA_EXCLUDED_CELLS") or []) != EXCLUDED_CELLS:
        raise ValueError("Retain the fixed new-optimization delay-buffer exclusion")
    if list(config["STA_CORNERS"]) != CORNERS:
        raise ValueError("Require all original nine STA corners")
    required = {"RUN_POST_GRT_DESIGN_REPAIR": True,
                "RUN_POST_GRT_RESIZER_TIMING": True,
                "GRT_DESIGN_REPAIR_MAX_SLEW_PCT": 60,
                "GRT_DESIGN_REPAIR_MAX_CAP_PCT": 30,
                "GRT_RESIZER_HOLD_SLACK_MARGIN": 0.1}
    for key, value in required.items():
        actual = config.get(key)
        valid = (type(actual) is bool and actual is value) if type(value) is bool else (
            type(actual) in (int, float, Decimal) and Decimal(str(actual)).is_finite()
            and Decimal(str(actual)) == Decimal(str(value)))
        if not valid:
            raise ValueError("Preserve the fixed standard repair assumption: " + key)


class StandardElectricalRepair(OpenROAD.RepairDesignPostGRT):
    def __init__(self, config, *args, **kwargs):
        validate_optimization_config(config)
        super().__init__(config, *args, **kwargs)


class AllCornerTimingPostGRT(OpenROAD.ResizerTimingPostGRT):
    def __init__(self, config, *args, **kwargs):
        validate_optimization_config(config)
        super().__init__(config.copy(RSZ_CORNERS=list(CORNERS)), *args, **kwargs)


class ElectricalRepairAfterTiming(StandardElectricalRepair):
    id = FINAL_REPAIR_STEP
    name = "Standard Electrical Repair After Timing (Generic V2)"


@Flow.factory.register("HuLLCirqGenericRouteClosureV2")
class GenericRouteClosureV2(Classic):
    Substitutions = {
        "OpenROAD.RepairDesignPostGRT": StandardElectricalRepair,
        "OpenROAD.ResizerTimingPostGRT": AllCornerTimingPostGRT,
        "+OpenROAD.ResizerTimingPostGRT": ElectricalRepairAfterTiming,
    }


if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
