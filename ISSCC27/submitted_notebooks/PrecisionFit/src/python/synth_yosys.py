"""
Run Yosys synthesis on a generated RTL file and parse the JSON cell-count
report.

The metric here is *total mapped cell count* after `abc -g cmos2`. It is a
relative area proxy: useful for ranking hundreds of candidate configurations
consistently, but it is NOT a physical area (no library, no place & route).
The Week 4 OpenLane/SKY130 flow is what produces real um^2 numbers.
"""
import json
import subprocess
from pathlib import Path

import paths

SYNTH_SCRIPT = paths.SYNTH_DIR / "yosys_synth.tcl"


def _find_module_stats(report: dict, module_name: str) -> dict:
    """
    Yosys keys modules by their internal name, which may carry a leading
    backslash (e.g. `\\fir_baseline`). Try the plain name, then the escaped
    form, then fall back to the only module if there is exactly one.
    """
    modules = report.get("modules", {})
    for key in (module_name, "\\" + module_name):
        if key in modules:
            return modules[key]
    if len(modules) == 1:
        return next(iter(modules.values()))
    raise KeyError(f"module {module_name!r} not found in Yosys report "
                   f"(have: {list(modules)})")


def synthesize(rtl_path, module_name: str, report_dir=None, timeout: int = 600) -> dict:
    """Synthesize one RTL file and return cell counts. Raises on failure."""
    report_dir = Path(report_dir) if report_dir else Path("/tmp")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{module_name}_yosys.json"

    cmd = ["yosys", "-c", str(SYNTH_SCRIPT), "--",
           str(rtl_path), module_name, str(report_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"Yosys failed for {module_name}:\n"
                           f"{result.stdout[-4000:]}\n{result.stderr[-4000:]}")
    if not report_path.exists():
        raise RuntimeError(f"Yosys produced no report for {module_name}")

    with open(report_path) as f:
        report = json.load(f)

    mod_stats = _find_module_stats(report, module_name)
    num_cells = mod_stats.get("num_cells_by_type", {})
    total_cells = int(sum(num_cells.values()))
    flop_cells = int(sum(c for t, c in num_cells.items() if "$_DFF" in t))
    comb_cells = total_cells - flop_cells

    return dict(
        module_name=module_name,
        total_cells=total_cells,
        flop_cells=flop_cells,
        comb_cells=comb_cells,
        cells_by_type=num_cells,
        report_path=str(report_path),
        raw_report=report,
    )


if __name__ == "__main__":
    from reference import FILTER_A_SPEC, design_filter
    from fixedpoint import FixedPointConfig
    from rtlgen import generate_rtl

    paths.ensure_dirs()
    h = design_filter(FILTER_A_SPEC)
    cfg = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14,
        acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=14,
        rounding="round", saturate_output=True,
    )
    rtl_path = generate_rtl(h, cfg, config_name="baseline_conservative")
    r = synthesize(rtl_path, "fir_baseline_conservative")
    print(f"Total cells: {r['total_cells']}  "
          f"(flops {r['flop_cells']}, comb {r['comb_cells']})")
    for cell_type, count in sorted(r["cells_by_type"].items(),
                                   key=lambda kv: -kv[1]):
        print(f"  {cell_type}: {count}")
