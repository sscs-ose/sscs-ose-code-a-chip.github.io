#!/usr/bin/env python3
"""Pinned OpenLane Classic plus bounded post-DRT repair; no check is removed.

Run inside the pinned image. The continuation mode imports only repaired design
views and source headers, discarding all historical signoff views and metrics.
The standard downstream flow must regenerate them before qualification.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sys

from openlane.common import Path as OLPath, set_tpe
from openlane.flows import Flow
from openlane.flows.classic import Classic
from openlane.steps import Step, StepError
from openlane.steps.openroad import DetailedRouting, GlobalRouting, OpenROADStep
from openlane.state import State, DesignFormat


SCRIPT = Path(__file__).with_name("dac27_post_drt.tcl")


def descriptor(path):
    path = Path(path)
    content = path.read_bytes()
    return {"path": str(path), "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()}


@Step.factory.register()
class PostDRTAntennaRepair(OpenROADStep):
    id = "DAC27.PostDRTAntennaRepair"
    name = "Bounded Post-DRT Antenna Repair"
    # GlobalRouting also carries the detailed-placement variables used by the
    # common legalization helper. Preserve the pinned Variable definitions.
    config_vars = list({v.name: v for v in
                        DetailedRouting.config_vars + GlobalRouting.config_vars}.values())

    def get_script_path(self):
        return str(SCRIPT)

    def run(self, state_in, **kwargs):
        route_drvs = state_in.metrics.get("route__drc_errors")
        if route_drvs is None or int(route_drvs) != route_drvs or route_drvs < 0:
            raise StepError("Missing or invalid detailed-routing violation count")
        if self.config["DRT_THREADS"] != 2:
            raise StepError("DAC27 recipe requires explicit DRT_THREADS=2")
        kwargs, env = self.extract_env(kwargs)
        env["DAC27_INPUT_ROUTE_DRVS"] = str(int(route_drvs))
        views, metrics = super().run(state_in, env=env, **kwargs)
        step_dir = Path(self.step_dir)
        lines = (step_dir / "repair_summary.tsv").read_text().splitlines()
        final = [line.split("\t") for line in lines if line.startswith("final\t")]
        baseline = [line.split("\t") for line in lines if line.startswith("baseline\t")]
        if len(final) != 1 or len(final[0]) != 4 or len(baseline) != 1:
            raise StepError("Missing unique native repair summary")
        passes, antenna, route_drvs = map(int, final[0][1:])
        if not 0 <= passes <= 2 or antenna != 0 or route_drvs != 0:
            raise StepError("Native bounded repair did not clear antenna and routing DRC")
        report = step_dir / (f"pass_{passes}.antenna.rpt" if passes else "before.antenna.rpt")
        if re.search(r"\(VIOLATED\)", report.read_text()):
            raise StepError("Native final antenna report still contains violations")
        if passes and (step_dir / f"pass_{passes}.drc").read_text().strip():
            raise StepError("Native reroute DRC report is not empty")
        metrics.update({"route__antenna_violation__count": antenna,
                        "route__drc_errors": route_drvs,
                        "dac27__post_drt_repair__passes": passes,
                        "dac27__post_drt_repair__baseline_antenna": int(baseline[0][1])})
        with (step_dir / "repair_result.json").open("x") as stream:
            json.dump({"status": "LOCAL_ANTENNA_AND_ROUTING_CLEAR",
                       "complete_physical_signoff": False,
                       "passes": passes, "max_passes": 2,
                       "baseline_antenna": int(baseline[0][1]),
                       "final_antenna": antenna, "route_drc": route_drvs,
                       "native_summary": descriptor(step_dir / "repair_summary.tsv"),
                       "final_antenna_report": descriptor(report),
                       "script": descriptor(SCRIPT)}, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return views, metrics


@Flow.factory.register()
class DAC27Classic(Classic):
    Steps = []
    for _step in Classic.Steps:
        Steps.append(_step)
        if _step.id == "OpenROAD.DetailedRouting":
            Steps.append(PostDRTAntennaRepair)


def repaired_state(initial_state, prefix=None):
    """Import geometry with only source-bound routing/synthesis counters."""
    if prefix is None and (Path(initial_state).name != "state_out.json"
            or not re.fullmatch(r"\d+-openroad-detailedrouting", Path(initial_state).parent.name)):
        raise ValueError("Direct continuation requires the native DetailedRouting output state")
    old = State.loads(Path(initial_state).read_text())
    views = {}
    inputs = [descriptor(initial_state)]
    for fmt, suffix in ((DesignFormat.ODB, ".odb"), (DesignFormat.DEF, ".def"),
                        (DesignFormat.NETLIST, ".nl.v"),
                        (DesignFormat.POWERED_NETLIST, ".pnl.v"),
                        (DesignFormat.SDC, ".sdc")):
        path = (Path(str(prefix) + suffix) if prefix is not None else Path(old[fmt])).resolve()
        inputs.append(descriptor(path))
        views[fmt] = OLPath(str(path))
    # These source-level headers contain design/port information only and are
    # required by the unchanged downstream stream-out/LVS steps.
    for key in ("json_h", "vh"):
        if old[key] is not None:
            inputs.append(descriptor(old[key]))
            views[key] = old[key]
    # TrDRC reads the router's counter. Bind it to the exact geometry source:
    # the native DRT state for direct continuation, or the round-1 repair log.
    # Every downstream extraction, DRC/LVS and timing stage runs anew.
    if prefix is None:
        route_drvs = old.metrics.get("route__drc_errors")
        if route_drvs is None or isinstance(route_drvs, bool) or int(route_drvs) != route_drvs or route_drvs < 0:
            raise ValueError("Source DetailedRouting state has no valid router DRV count")
    else:
        route_log = Path(prefix).parent / "stdout.log"
        inputs.append(descriptor(route_log))
        counts = re.findall(r"^POST_DRT_AFTER_DRC_COUNT ([0-9]+)\s*$",
                            route_log.read_text(), re.M)
        if len(counts) != 1:
            raise ValueError("Repaired continuation needs the unique native router DRV count")
        route_drvs = int(counts[0])
    unmapped = old.metrics.get("design__instance_unmapped__count")
    if unmapped is None or int(unmapped) != unmapped or unmapped < 0:
        raise ValueError("Source state has no valid synthesis unmapped-cell count")
    metrics = {"route__drc_errors": int(route_drvs),
               "design__instance_unmapped__count": int(unmapped)}
    return State(views, metrics=metrics), inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--run-tag", "--tag", dest="tag", required=True)
    parser.add_argument("--flow", choices=["DAC27Classic"], default="DAC27Classic")
    parser.add_argument("--manual-pdk", action="store_true")
    parser.add_argument("--pdk-root", default="/pdk")
    parser.add_argument("--pdk", default="sky130A")
    parser.add_argument("--scl", default="sky130_fd_sc_hd")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--hide-progress-bar", action="store_true")
    parser.add_argument("--initial-state")
    parser.add_argument("--repaired-prefix")
    parser.add_argument("--from-step")
    parser.add_argument("--smoke-config", action="store_true",
                        help="Resolve config and step sequence only; no EDA execution")
    args = parser.parse_args()
    if args.jobs != 2:
        parser.error("The DAC27 execution recipe fixes --jobs 2")
    if args.repaired_prefix and not args.initial_state:
        parser.error("--repaired-prefix requires --initial-state")
    if args.initial_state and args.from_step != "DAC27.PostDRTAntennaRepair":
        parser.error("Repaired continuation must start at DAC27.PostDRTAntennaRepair")
    if args.from_step and not args.initial_state:
        parser.error("Partial fresh runs are not supported")
    directory = Path(args.run_dir).resolve()
    if directory.exists():
        parser.error("Run directory already exists; evidence is never overwritten")
    if args.hide_progress_bar:
        from openlane.logging import options
        options.set_show_progress_bar(False)
    set_tpe(ThreadPoolExecutor(max_workers=args.jobs))
    flow = DAC27Classic(args.config, pdk_root=args.pdk_root,
                       pdk=args.pdk, scl=args.scl)
    if flow.config["DRT_THREADS"] != 2:
        parser.error("Config must explicitly set DRT_THREADS=2")
    if args.smoke_config:
        directory.mkdir(parents=True)
        (directory / "resolved.json").write_text(flow.config.dumps())
        (directory / "steps.json").write_text(json.dumps([s.id for s in flow.Steps], indent=2) + "\n")
        print("DAC27_CONFIG_RESOLUTION_PASS")
        return 0
    state = None
    if args.initial_state:
        state, inputs = repaired_state(args.initial_state, args.repaired_prefix)
        # Pre-create only an empty run directory. Flow.start treats it as new.
        directory.mkdir(parents=True)
        # Store import provenance beside the run; writing into it would make
        # Flow.start treat it as a prior run and try to load previous steps.
        with directory.with_name(directory.name + ".import.json").open("x") as stream:
            json.dump({"inputs": inputs, "imported_state": state.to_raw_dict(),
                       "preserved_upstream_metric_keys": ["design__instance_unmapped__count"],
                       "route_metric_source_kind": ("REPAIRED_ROUTE_LOG" if args.repaired_prefix
                                                    else "DETAILED_ROUTE_STATE"),
                       "reroute_metric_source": (str(Path(args.repaired_prefix).parent / "stdout.log")
                                                 if args.repaired_prefix else str(Path(args.initial_state))),
                       "discarded_other_historical_metrics": True,
                       "from_step": args.from_step}, stream, indent=2, default=str)
            stream.write("\n")
    flow.start(tag=args.tag, with_initial_state=state, frm=args.from_step,
               _force_run_dir=str(directory), overwrite=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
