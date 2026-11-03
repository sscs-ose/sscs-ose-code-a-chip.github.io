from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Apply custom Matplotlib style
plt.style.use(Path(__file__).parent / "own.mplstyle")


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

DATASETS = {
    "Pre-EM": Path(
        "/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/02_preEM_60GHz_MPA_xyce/eval_02_preEM_60GHz_MPA_xyce_Irf_in-0.1e-3-35e-3_.csv"
    ),
    # "Post-EM": Path(
    #     "/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/03_postEM_60GHz_MPA_xyce/eval_03_postEM_60GHz_MPA_xyce_Irf_in-0.1e-3-35e-3_.csv"
    # ),
}

# Consistent colors across plots
COLORS = {
    "Pre-EM":          "tab:orange",
    "Post-EM":         "tab:green",
}


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def load_pae_data(filepath):
    """Load and sort RF input power and pae from a simulation CSV."""

    df_eval = pd.read_csv(filepath)

    # Extract RF input power and gain
    df_rf_input_power = pd.to_numeric(
        df_eval["Power_rf_in_dBm"],
        errors="coerce",
    )

    pae = pd.to_numeric(
        df_eval["PAE_percent"],
        errors="coerce",
    )

    # Remove invalid rows
    valid = (
        df_rf_input_power.notna()
        & pae.notna()
        & np.isfinite(df_rf_input_power)
        & np.isfinite(pae)
    )

    df_eval = pd.DataFrame({
        "Power_rf_in_dBm": df_rf_input_power[valid],
        "PAE_percent": pae[valid],
    })

    # Sort by RF input power
    df_rf_input_power_sorted = (
        df_eval.sort_values(by="Power_rf_in_dBm")
        .reset_index(drop=True)
    )

    if df_rf_input_power_sorted.empty:
        raise ValueError(f"No valid data found in {filepath}")

    return (
        df_rf_input_power_sorted["Power_rf_in_dBm"].to_numpy(),
        df_rf_input_power_sorted["PAE_percent"].to_numpy(),
    )


# ----------------------------------------------------------------------
# Plot
# ----------------------------------------------------------------------

fig, ax = plt.subplots()

for label, filepath in DATASETS.items():

    if not filepath.is_file():
        raise FileNotFoundError(
            f"Could not find CSV file: {filepath}"
        )

    input_power, pae = load_pae_data(filepath)

    # Plot gain curve
    ax.plot(
        input_power,
        pae,
        color=COLORS[label],
        label=(
            f"{label} "
            f"@ 60 GHz"
        ),
    )


# ----------------------------------------------------------------------
# Formatting
# ----------------------------------------------------------------------

ax.set_xlabel("RF input power (dBm)")
ax.set_ylabel(r"PAE (\%)")

ax.legend()
ax.grid(True, alpha=0.3)

fig.tight_layout()
plt.show()