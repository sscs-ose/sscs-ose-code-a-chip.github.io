"""Fixed standard LibreLane flow with separate electrical/timing repair corners.

Only the timing-repair step receives all original STA corners. The design-repair
step keeps the configured slow corner. Upstream Tcl and final constraints are
unchanged. This source is frozen and hash-checked for each actual v5 run.
"""
from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.steps import OpenROAD


class AllCornerTimingPostGRT(OpenROAD.ResizerTimingPostGRT):
    def __init__(self, config, *args, **kwargs):
        corners = list(config["STA_CORNERS"])
        if len(corners) != 9 or len(set(corners)) != 9:
            raise ValueError("Require the original nine STA corners")
        super().__init__(config.copy(RSZ_CORNERS=corners), *args, **kwargs)


@Flow.factory.register("HuLLCirqRouteClosureV5")
class RouteClosureV5(Classic):
    Substitutions = {"OpenROAD.ResizerTimingPostGRT": AllCornerTimingPostGRT}


if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
