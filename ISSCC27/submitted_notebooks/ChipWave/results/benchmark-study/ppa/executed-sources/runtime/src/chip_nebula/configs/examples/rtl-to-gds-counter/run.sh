#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
generated_layout=0
if [[ -f "$case_dir/flow-definition.json" ]]; then
    generated_layout=1
    real_project_root="$(cd -- "$case_dir/../.." && pwd -P)"
else
    real_project_root="$(cd -- "$case_dir" && pwd -P)"
fi

# Some EDA frontends cannot open Tcl/RTL files when any parent directory uses
# non-ASCII characters (or characters that Make treats as separators). Keep
# the immutable snapshot in place, but expose it through an ASCII-only alias
# for the duration of this run.
project_alias_container=""
project_alias=""
repo_root="$real_project_root"
if [[ ! "$real_project_root" =~ ^[A-Za-z0-9_./-]+$ ]]; then
    project_alias_container="$(mktemp -d /tmp/chip-nebula-rtl2gds.XXXXXXXX)"
    project_alias="$project_alias_container/project"
    ln -s -- "$real_project_root" "$project_alias"
    repo_root="$project_alias"
    cleanup_project_alias() {
        rm -f -- "$project_alias"
        rmdir -- "$project_alias_container" 2>/dev/null || true
    }
    trap cleanup_project_alias EXIT
fi
if [[ "$generated_layout" == "1" ]]; then
    case_dir="$repo_root/physical/chip-nebula"
    constraint_file="$case_dir/constraints.sdc"
else
    case_dir="$repo_root"
    constraint_file="$case_dir/constraint.sdc"
fi
source "$case_dir/tool-versions.env"

action="${1:-all}"
requested_work_root="${CHIP_NEBULA_RTL2GDS_WORK_ROOT:-$repo_root/build/rtl-to-gds-counter}"
if [[ -n "$project_alias" && "$requested_work_root" == "$real_project_root" ]]; then
    requested_work_root="$repo_root"
elif [[ -n "$project_alias" && "$requested_work_root" == "$real_project_root/"* ]]; then
    requested_work_root="$repo_root/${requested_work_root#"$real_project_root/"}"
fi
if [[ "$requested_work_root" != /* ]]; then
    requested_work_root="$repo_root/$requested_work_root"
fi
work_root="$(realpath -ms -- "$requested_work_root")"
tool_root="${CHIP_NEBULA_RTL2GDS_TOOL_ROOT:-$repo_root/build/rtl2gds-tools}"
orfs_root="${ORFS_ROOT:-$tool_root/OpenROAD-flow-scripts}"
variant="${FLOW_VARIANT:-smoke}"
num_cores="${NUM_CORES:-2}"
flow_home=""

case "$action" in
    all|physical)
        if [[ -f "$orfs_root/flow/Makefile" ]]; then
            flow_home="$orfs_root/flow"
        elif [[ -f "$orfs_root/Makefile" ]]; then
            flow_home="$orfs_root"
            orfs_root="$(cd "$flow_home/.." && pwd)"
        else
            echo "ERROR: ORFS_ROOT does not contain flow/Makefile: $orfs_root" >&2
            exit 2
        fi
        ;;
esac

local_bin="$tool_root/bin"
choose_tool() {
    local variable_value="$1"
    local local_candidate="$2"
    local command_name="$3"
    if [[ -n "$variable_value" ]]; then
        printf '%s\n' "$variable_value"
    elif [[ -x "$local_candidate" ]]; then
        printf '%s\n' "$local_candidate"
    elif command -v "$command_name" >/dev/null 2>&1; then
        command -v "$command_name"
    else
        echo "ERROR: required tool not found: $command_name" >&2
        exit 2
    fi
}

openroad_exe=""
yosys_exe=""
klayout_cmd=""
iverilog_exe=""
vvp_exe=""
python_exe=""
openroad_version=""
yosys_version=""
klayout_version=""

case "$action" in
    all|sim)
        iverilog_exe="$(choose_tool "${IVERILOG_EXE:-}" /usr/bin/iverilog iverilog)"
        vvp_exe="$(choose_tool "${VVP_EXE:-}" /usr/bin/vvp vvp)"
        ;;
esac

case "$action" in
    all|physical)
        openroad_exe="$(choose_tool "${OPENROAD_EXE:-}" "$local_bin/openroad" openroad)"
        yosys_exe="$(choose_tool "${YOSYS_EXE:-}" "$local_bin/yosys" yosys)"
        klayout_cmd="$(choose_tool "${KLAYOUT_CMD:-}" "$local_bin/klayout" klayout)"
        python_exe="$(choose_tool "${PYTHON_EXE:-}" /usr/bin/python3 python3)"
        openroad_version="$("$openroad_exe" -version | head -n 1)"
        yosys_version="$("$yosys_exe" -V | head -n 1)"
        klayout_version="$("$klayout_cmd" -v | head -n 1)"
        if [[ "${ALLOW_TOOL_VERSION_MISMATCH:-0}" != "1" ]]; then
            [[ "$openroad_version" == *"$OPENROAD_VERSION"* ]] || {
                echo "ERROR: expected OpenROAD $OPENROAD_VERSION, got: $openroad_version" >&2
                exit 2
            }
            [[ "$yosys_version" == *"$YOSYS_VERSION"* ]] || {
                echo "ERROR: expected Yosys $YOSYS_VERSION, got: $yosys_version" >&2
                exit 2
            }
            [[ "$klayout_version" == *"$KLAYOUT_VERSION"* ]] || {
                echo "ERROR: expected KLayout $KLAYOUT_VERSION, got: $klayout_version" >&2
                exit 2
            }
        fi
        ;;
esac

check_physical_inputs() {
    for required in "$constraint_file" "$case_dir/config.mk" \
        "$case_dir/prepare_orfs.py" "$case_dir/inspect_gds.py" \
        "$case_dir/klayout.sh" "$case_dir/filter_lvs_cdl.py"; do
        if [[ ! -s "$required" ]]; then
            echo "ERROR: physical input is missing or empty: $required" >&2
            exit 2
        fi
    done
}

run_simulation() {
    echo "CHIP_NEBULA_STAGE simulation"
    mkdir -p "$work_root/simulation/build"
    (
        cd "$work_root/simulation"
        "$iverilog_exe" -g2012 -s nebula_counter_tb \
            -o build/nebula_counter_sim \
            "$case_dir/rtl/nebula_counter.v" \
            "$case_dir/tb/nebula_counter_tb.v"
        "$vvp_exe" build/nebula_counter_sim | tee build/simulation.log
    )
}

run_physical() {
    check_physical_inputs
    echo "CHIP_NEBULA_STAGE synthesis"
    local actual_orfs_commit
    actual_orfs_commit=""
    if [[ -e "$orfs_root/.git" ]]; then
        actual_orfs_commit="$(git -C "$orfs_root" rev-parse HEAD 2>/dev/null || true)"
    fi
    if [[ -z "$actual_orfs_commit" && -f "$orfs_root/ORFS_REVISION" ]]; then
        actual_orfs_commit="$(tr -d '[:space:]' < "$orfs_root/ORFS_REVISION")"
    fi
    if [[ "$actual_orfs_commit" != "$ORFS_COMMIT" ]]; then
        echo "ERROR: ORFS commit mismatch" >&2
        echo "  expected: $ORFS_COMMIT" >&2
        echo "  actual:   ${actual_orfs_commit:-unknown}" >&2
        echo "Set ORFS_ROOT to the pinned checkout documented in README.md." >&2
        exit 2
    fi

    for required in \
        "$flow_home/platforms/sky130hd/gds/sky130_fd_sc_hd.gds" \
        "$flow_home/platforms/sky130hd/drc/sky130hd.lydrc" \
        "$flow_home/platforms/sky130hd/lvs/sky130hd.lylvs" \
        "$flow_home/platforms/sky130hd/cdl/sky130hd.cdl"; do
        if [[ ! -s "$required" ]]; then
            echo "ERROR: required Sky130 platform file is missing: $required" >&2
            exit 2
        fi
    done

    local overlay_dir="$work_root/orfs-overlay"
    local orfs_work="$work_root/orfs-work"
    mkdir -p "$overlay_dir/scripts" "$orfs_work"
    cp -a "$flow_home/scripts/." "$overlay_dir/scripts/"
    cp "$case_dir/klayout.sh" "$case_dir/filter_lvs_cdl.py" "$overlay_dir/scripts/"
    chmod +x "$overlay_dir/scripts/klayout.sh"
    "$python_exe" "$case_dir/prepare_orfs.py" \
        "$overlay_dir/scripts/final_outputs.tcl"

    local make_args=(
        -C "$flow_home"
        "DESIGN_CONFIG=$case_dir/config.mk"
        "FLOW_VARIANT=$variant"
        "WORK_HOME=$orfs_work"
        "SCRIPTS_DIR=$overlay_dir/scripts"
        "OPENROAD_EXE=$openroad_exe"
        "YOSYS_EXE=$yosys_exe"
        "KLAYOUT_CMD=$klayout_cmd"
        "PYTHON_EXE=$python_exe"
        "NUM_CORES=$num_cores"
    )

    make "${make_args[@]}" all
    make "${make_args[@]}" drc lvs

    local result_dir="$orfs_work/results/sky130hd/nebula_counter/$variant"
    local report_dir="$orfs_work/reports/sky130hd/nebula_counter/$variant"
    local log_dir="$orfs_work/logs/sky130hd/nebula_counter/$variant"
    local gds="$result_dir/6_final.gds"
    local drc_count_file="$report_dir/6_drc_count.rpt"
    local lvs_log="$log_dir/6_lvs.log"
    local final_metrics="$log_dir/6_report.json"
    local route_metrics="$log_dir/5_2_route.json"
    local gds_info="$work_root/gds-summary.json"

    [[ -s "$gds" ]] || {
        echo "ERROR: final GDSII was not generated" >&2
        exit 1
    }
    [[ -s "$drc_count_file" ]] || {
        echo "ERROR: DRC count report is missing" >&2
        exit 1
    }
    [[ -s "$lvs_log" ]] || {
        echo "ERROR: LVS report is missing" >&2
        exit 1
    }
    [[ -s "$final_metrics" ]] || {
        echo "ERROR: final metrics are missing" >&2
        exit 1
    }
    [[ -s "$route_metrics" ]] || {
        echo "ERROR: route metrics are missing" >&2
        exit 1
    }

    "$klayout_cmd" -b -r "$case_dir/inspect_gds.py" \
        -rd "in_gds=$gds" -rd "out_json=$gds_info"

    local gds_sha
    gds_sha="$(sha256sum "$gds" | cut -d ' ' -f 1)"

    local simulation_status="not_run"
    if grep -Fq "PASS: nebula_counter functional simulation" \
        "$work_root/simulation/build/simulation.log" 2>/dev/null; then
        simulation_status="passed"
    fi

    "$python_exe" - "$work_root/run-summary.json" "$gds" "$gds_sha" \
    "$actual_orfs_commit" "$openroad_version" "$yosys_version" \
    "$klayout_version" "$gds_info" "$final_metrics" "$route_metrics" \
    "$simulation_status" "$constraint_file" "$drc_count_file" \
    "$lvs_log" <<'PY'
import json
import pathlib
import re
import sys

(
    output_path,
    gds_path,
    gds_sha,
    orfs_commit,
    openroad_version,
    yosys_version,
    klayout_version,
    gds_info_path,
    final_metrics_path,
    route_metrics_path,
    simulation_status,
    constraint_path,
    drc_count_path,
    lvs_log_path,
) = sys.argv[1:]
gds_info = json.loads(pathlib.Path(gds_info_path).read_text(encoding="utf-8"))
metrics = json.loads(pathlib.Path(final_metrics_path).read_text(encoding="utf-8"))
route_metrics = json.loads(pathlib.Path(route_metrics_path).read_text(encoding="utf-8"))
constraint_text = pathlib.Path(constraint_path).read_text(encoding="utf-8")
drc_text = pathlib.Path(drc_count_path).read_text(encoding="utf-8").strip()
lvs_text = pathlib.Path(lvs_log_path).read_text(encoding="utf-8", errors="replace")
clock_periods = re.findall(
    r"(?m)^\s*create_clock\b[^\n]*\s-period\s+"
    r"([0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:\s|$)",
    constraint_text,
)
if len(clock_periods) != 1:
    raise SystemExit(
        "expected exactly one literal create_clock -period in the configured SDC, "
        f"found {len(clock_periods)}"
    )
clock_period_ns = float(clock_periods[0])
route_violations = route_metrics["detailedroute__route__drc_errors"]
setup_violations = metrics["finish__timing__drv__setup_violation_count"]
hold_violations = metrics["finish__timing__drv__hold_violation_count"]
if not re.fullmatch(r"[0-9]+", drc_text):
    raise SystemExit(f"DRC count report is not an integer: {drc_text!r}")
drc_violations = int(drc_text)
lvs_status = (
    "matched"
    if "INFO : Congratulations! Netlists match." in lvs_text
    else "mismatched"
)
failures = []
if route_violations != 0:
    failures.append(f"detailed routing violations={route_violations}")
if drc_violations != 0:
    failures.append(f"DRC violations={drc_violations}")
if lvs_status != "matched":
    failures.append("LVS netlists do not match")
if setup_violations != 0 or hold_violations != 0:
    setup_slack = metrics["finish__timing__setup__ws"]
    hold_slack = metrics["finish__timing__hold__ws"]
    fmax_mhz = metrics["finish__timing__fmax"] / 1_000_000
    failures.append(
        f"timing violations: setup={setup_violations}, hold={hold_violations}; "
        f"setup slack={setup_slack:g} ns, hold slack={hold_slack:g} ns; "
        f"estimated Fmax={fmax_mhz:g} MHz"
    )
summary = {
    "status": (
        "failed" if failures
        else ("passed" if simulation_status == "passed" else "physical_passed")
    ),
    "flow": "rtl-to-gds",
    "platform": "sky130hd",
    "design": "nebula_counter",
    "functional_simulation": simulation_status,
    "detailed_routing_violations": route_violations,
    "drc_violations": drc_violations,
    "lvs": lvs_status,
    "metrics": {
        "clock_period_ns": clock_period_ns,
        "setup_slack_ns": metrics["finish__timing__setup__ws"],
        "hold_slack_ns": metrics["finish__timing__hold__ws"],
        "setup_violations": setup_violations,
        "hold_violations": hold_violations,
        "estimated_fmax_hz": metrics["finish__timing__fmax"],
        "estimated_total_power_w": metrics["finish__power__total"],
        "die_area_um2": metrics["finish__design__die__area"],
        "placed_instance_area_um2": metrics["finish__design__instance__area"],
        "placed_instance_utilization": metrics[
            "finish__design__instance__utilization"
        ],
        "standard_cell_count": metrics["finish__design__instance__count__stdcell"],
        "worst_vdd_ir_drop_v": metrics[
            "finish__design_powergrid__drop__worst__net:VDD__corner:default"
        ],
    },
    "gds": {
        "path": gds_path,
        "sha256": gds_sha,
        **gds_info,
    },
    "tools": {
        "orfs_commit": orfs_commit,
        "openroad": openroad_version,
        "yosys": yosys_version,
        "klayout": klayout_version,
    },
}
if failures:
    summary["failed_stage"] = "signoff"
    summary["failure_reason"] = "; ".join(failures)
pathlib.Path(output_path).write_text(
    json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
if failures:
    raise SystemExit("ERROR: " + summary["failure_reason"])
PY

    echo
    echo "PASS: RTL-to-GDS flow completed"
    echo "  GDSII:  $gds"
    echo "  DRC:    0 violations"
    echo "  LVS:    matched"
    echo "  Summary: $work_root/run-summary.json"
}

case "$action" in
    preflight)
        check_physical_inputs
        echo "PASS: physical project inputs are complete"
        ;;
    all)
        run_simulation
        run_physical
        ;;
    sim)
        run_simulation
        ;;
    physical)
        run_physical
        ;;
    clean)
        if [[ "$work_root" == "/" || "$work_root" == "$repo_root" || ${#work_root} -lt 12 ]]; then
            echo "ERROR: refusing to clean unsafe work root: $work_root" >&2
            exit 2
        fi
        rm -rf "$work_root"
        ;;
    *)
        echo "Usage: $0 [preflight|all|sim|physical|clean]" >&2
        exit 2
        ;;
esac
