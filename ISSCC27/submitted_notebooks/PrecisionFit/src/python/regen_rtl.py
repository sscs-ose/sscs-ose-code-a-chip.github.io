"""
Regenerate the committed RTL files from the current templates and check that
the simulation-visible text is unchanged. Used when the template gains
ifdef-guarded sections (formal layer) that must not perturb the design.

Committed artifacts touched (all regenerated in place):
  src/verilog/rtl/fir_baseline_conservative.v   (verify_rtl.py demo config)
  src/verilog/rtl/fir_best_uniform.v            (headline: best uniform)
  src/verilog/rtl/fir_conservative_uniform.v    (headline: conservative)
  src/verilog/rtl/fir_sensitivity_guided.v      (headline: sensitivity-guided)
  src/verilog/rtl/fir_notebook_baseline.v       (notebook Q2.10 demo)
  src/verilog/rtl/fir_notebook_nonuniform.v     (notebook per-tap demo)
"""
from pathlib import Path

import numpy as np

import paths
from reference import FILTER_A_SPEC, design_filter
from fixedpoint import FixedPointConfig
from rtlgen import generate_rtl, generate_rtl_nonuniform
from build_comparison import headline_configs


def sim_visible_lines(text: str):
    """Lines a simulator/synthesizer sees: code minus comments, and minus any
    `ifdef FORMAL ... `endif region (the formal layer is invisible to sim)."""
    lines, stack = [], []          # stack of active `ifdef names (nested!)
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].rstrip()
        s = line.strip()
        if not s:
            continue
        if s.startswith("`ifdef") or s.startswith("`ifndef"):
            stack.append(s.split()[1] if len(s.split()) > 1 else "?")
            continue
        if s.startswith("`endif"):
            if stack:
                stack.pop()
            continue
        if "FORMAL" in stack:      # inside the formal-only region
            continue
        lines.append(line)
    return lines


def main():
    paths.ensure_dirs()
    h = design_filter(FILTER_A_SPEC)

    # The sweep stages generate hundreds of throwaway RTL files (fir_u_*,
    # fir_s_*, fir_b_*, fir_check_*); those are gitignored scratch, so the
    # drift check below is restricted to the files this script regenerates --
    # exactly the set tracked in git under src/verilog/rtl/.
    generated = []

    # 1. Headline designs (module/config names must match the committed files).
    heads = headline_configs(h)   # returns rebuilt paths; rewrites the .v files
    generated += [Path(c["rtl_path"]).name for c in heads.values()]

    # 2. verify_rtl.py demo config -> fir_baseline_conservative.v
    cfg_demo = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14,
        acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=14,
        rounding="round", saturate_output=True,
    )
    generated.append(Path(generate_rtl(
        h, cfg_demo, config_name="baseline_conservative")).name)

    # 3. Notebook-flow demos (values must match the committed files exactly).
    cfg_nb = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14,
        acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=14,
        rounding="round", saturate_output=True,
    )
    generated.append(Path(generate_rtl(
        h, cfg_nb, config_name="notebook_baseline")).name)
    bits = np.array([14, 14, 14, 12, 16, 12, 16, 10, 10])
    generated.append(Path(generate_rtl_nonuniform(
        h, cfg_nb, bits, config_name="notebook_nonuniform")).name)

    # 4. Drift check: for every RTL file this script regenerates, the diff
    # against git HEAD must be confined to comment lines or the formal block
    # (`ifdef FORMAL ... `endif).
    import subprocess
    files = sorted(set(generated))
    tracked = subprocess.run(
        ["git", "ls-files", "src/verilog/rtl"], cwd=paths.ROOT,
        capture_output=True, text=True).stdout.splitlines()
    tracked_names = sorted(Path(t).name for t in tracked if t.endswith(".v"))
    unchecked = [n for n in tracked_names if n not in files]
    if unchecked:
        print(f"note: tracked but not regenerated (not checked): {unchecked}")
    bad = []
    for name in files:
        p = paths.RTL_DIR / name
        old = subprocess.run(["git", "show", f"HEAD:./{p.relative_to(paths.ROOT)}"],
                             cwd=paths.ROOT, capture_output=True, text=True).stdout
        if not old:
            bad.append((name, "no HEAD version"))
            continue
        old_sim = sim_visible_lines(old)
        new_sim = sim_visible_lines(p.read_text())
        if old_sim != new_sim:
            added = [l for l in new_sim if l not in old_sim]
            bad.append((name, f"sim-visible drift, first added line: {added[:1]}"))
    if bad:
        for name, why in bad:
            print(f"DRIFT  {name}: {why}")
        raise SystemExit(1)
    print(f"All {len(files)} committed RTL files: simulation-visible text "
          "unchanged (edits confined to comments / the formal block).")


if __name__ == "__main__":
    main()
