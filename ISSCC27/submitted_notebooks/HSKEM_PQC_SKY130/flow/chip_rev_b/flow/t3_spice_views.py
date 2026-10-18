"""Macro views with the SPICE clock-to-output delay, one directory per sign-off corner (plan item 2.2, step 2; tier-3 gate).

    t3_spice_views.py <sweep dir> <out dir> [corner ...]        (default corners: ss ff tt)

<sweep dir>/<corner>/<macro>/energy.json are the results of chip_v2/sram_timing_sweep.sh (clk_to_dout_ns.max, from the
falling clock edge, 10 fF load). For every macro view in the chip's view directory, <out dir>/<corner>/ gets a copy whose
dout cell_rise/cell_fall tables carry the measured worst delay (codeachip/scripts/spice_macro_lib.py). A macro type not
measured at a corner takes the largest delay increase (SPICE minus view) measured at that corner for any type, and is
marked provisional; <out dir>/<corner>/views.json records, for every type, the view delay, the delay used and its source.
Only the output delay changes: input setup/hold keep the view's values (not measured).
SPDX-License-Identifier: Apache-2.0
"""
import glob
import importlib.util
import json
import os
import sys

VIEWS = "/mnt/d/TKVM_ATTT_2026_test/report/a2_macro_link_smoke/run.rjfysF/derived_liberty"
TOOL = "/mnt/d/TKVM_ATTT_2026_test/codeachip/scripts/spice_macro_lib.py"
spec = importlib.util.spec_from_file_location("spice_macro_lib", TOOL)
sml = importlib.util.module_from_spec(spec); spec.loader.exec_module(sml)


def main(sweep, out, corners):
    libs = sorted(glob.glob(f"{VIEWS}/*.physical.lib"))
    assert libs, VIEWS
    for c in corners:
        rows, meas = {}, {}
        for lib in libs:
            macro = os.path.basename(lib).split("_TT_")[0]
            text = open(lib, newline="").read()
            view = max(sml.at_load(text[a:b], text) for a, b, _ in sml.tables(text))
            j = f"{sweep}/{c}/{macro}/energy.json"
            d = json.load(open(j)).get("clk_to_dout_ns", {}) if os.path.exists(j) else {}
            if d.get("max") and all(json.load(open(j)).get("reads_correct", [False])):
                meas[macro] = d["max"]
            rows[macro] = {"lib": lib, "view_ns": round(view, 3)}
        if not meas:
            print(f"{c}: no measurement, skipped"); continue
        os.makedirs(f"{out}/{c}", exist_ok=True)
        worst = max(meas, key=lambda m: meas[m] - rows[m]["view_ns"])
        dmax = meas[worst] - rows[worst]["view_ns"]
        for macro, r in rows.items():
            if macro in meas:
                used, src = meas[macro], "measured"
            else:
                used, src = r["view_ns"] + dmax, f"provisional: view + largest measured increase ({worst}, +{dmax:.3f} ns)"
            sml.main(r["lib"], f"{out}/{c}/{os.path.basename(r['lib'])}", used)
            r.update(used_ns=round(used, 3), source=src)
            print(f"{c} {macro:34s} view {r['view_ns']:.3f} -> {used:.3f} ns  {src}")
        json.dump({"corner": c, "sweep": sweep, "macros": rows}, open(f"{out}/{c}/views.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or ["ss", "ff", "tt"])
