"""
Full Week 2 sweep: accuracy-passing configs from search.py get RTL generated
and synthesized. Produces the CSV that feeds the Week 3 Pareto plot.

Only configs that already pass the error budget are synthesized -- there is no
point spending synthesis time on candidates that will be discarded.

Also gives the guide's section 4.2 sanity check a home: synthesize a few
configs of very different widths first and confirm cell count moves in a
sensible direction *before* trusting the metric across the whole sweep.
"""
import pandas as pd
from tqdm import tqdm

import paths
from reference import FILTER_A_SPEC, design_filter, make_test_signals
from search import uniform_sweep
from rtlgen import generate_rtl
from synth_yosys import synthesize


def synth_config(h, cfg, coeff_bits, input_bits, acc_guard, tag_prefix="u"):
    tag = f"{tag_prefix}_c{coeff_bits}_i{input_bits}_g{acc_guard}"
    rtl_path = generate_rtl(h, cfg, config_name=tag)
    result = synthesize(rtl_path, f"fir_{tag}")
    return tag, rtl_path, result


def synthesize_uniform_passing(h, passing, tag_prefix="u") -> pd.DataFrame:
    """Generate + synthesize RTL for every passing uniform config."""
    rows = []
    for _, row in tqdm(passing.iterrows(), total=len(passing)):
        cfg = row["cfg"]
        tag = (f"{tag_prefix}_c{row['coeff_bits']}_i{row['input_bits']}"
               f"_g{row['acc_guard']}")
        rtl_path = generate_rtl(h, cfg, config_name=tag)
        module_name = f"fir_{tag}"
        try:
            res = synthesize(rtl_path, module_name)
            rows.append(dict(
                tag=tag,
                module_name=module_name,
                # repo-relative so committed CSVs are machine-independent
                rtl_path=paths.rel(rtl_path),
                total_cells=res["total_cells"],
                flop_cells=res["flop_cells"],
                comb_cells=res["comb_cells"],
                coeff_bits=row["coeff_bits"],
                input_bits=row["input_bits"],
                acc_guard=row["acc_guard"],
                avg_bits_per_unique_coeff=float(row["coeff_bits"]),
                rms_error_wideband=row["rms_error_wideband"],
                snr_db_wideband=row["snr_db_wideband"],
                stopband_atten_db=row["stopband_atten_db"],
                passband_ripple_db=row["passband_ripple_db"],
            ))
        except RuntimeError as e:
            print(f"  synthesis failed for {tag}: {e}")
    return pd.DataFrame(rows).sort_values("total_cells")


def main():
    paths.ensure_dirs()
    h = design_filter(FILTER_A_SPEC)
    sigs = make_test_signals(FILTER_A_SPEC["fs"], n_samples=2048)

    df = uniform_sweep(h, FILTER_A_SPEC, sigs)
    df.drop(columns=["cfg"]).to_csv(paths.SWEEPS_DIR / "uniform_sweep.csv", index=False)
    passing = df[df["passes_error_budget"]].copy()
    print(f"{len(passing)} of {len(df)} configs pass the error budget -- "
          f"synthesizing all of them")

    # --- sanity check on two very different widths first (guide 4.2) -----------
    lo = passing.loc[passing["coeff_bits"].idxmin()]
    hi = passing.loc[passing["coeff_bits"].idxmax()]
    print("\nTwo-point sanity check before the full run:")
    for label, row in (("narrowest", lo), ("widest", hi)):
        cfg = row["cfg"]
        tag = f"check_{label}_c{row['coeff_bits']}"
        rtl_path = generate_rtl(h, cfg, config_name=tag)
        res = synthesize(rtl_path, f"fir_{tag}")
        print(f"  {label:>9}: coeff_bits={row['coeff_bits']:2d} "
              f"input_bits={row['input_bits']:2d} -> {res['total_cells']:6d} cells")

    synth_df = synthesize_uniform_passing(h, passing)
    out = paths.SWEEPS_DIR / "uniform_sweep_synth.csv"
    synth_df.to_csv(out, index=False)
    print(f"\nSynthesized {len(synth_df)} configs successfully -> {paths.rel(out)}")
    print(synth_df[["tag", "total_cells", "rms_error_wideband"]].head(10).to_string(index=False))
    return synth_df


if __name__ == "__main__":
    main()
