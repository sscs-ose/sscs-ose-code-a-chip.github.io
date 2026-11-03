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
    "Post-EM": Path(
        "/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/03_postEM_60GHz_MPA_xyce/eval_03_postEM_60GHz_MPA_xyce_Irf_in-0.1e-3-35e-3_.csv"
    ),
}

# Consistent colors across plots
COLORS = {
    "Pre-EM":          "tab:orange",
    "Post-EM":         "tab:green",
}


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def load_gain_data(filepath):
    """Load and sort RF input power and gain from a simulation CSV."""

    df_eval = pd.read_csv(filepath)

    # Extract RF input power and gain
    df_rf_input_power = pd.to_numeric(
        df_eval["Power_rf_in_dBm"],
        errors="coerce",
    )

    gain = pd.to_numeric(
        df_eval["Gain_db"],
        errors="coerce",
    )

    # Remove invalid rows
    valid = (
        df_rf_input_power.notna()
        & gain.notna()
        & np.isfinite(df_rf_input_power)
        & np.isfinite(gain)
    )

    df_eval = pd.DataFrame({
        "Power_rf_in_dBm": df_rf_input_power[valid],
        "Gain_db": gain[valid],
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
        df_rf_input_power_sorted["Gain_db"].to_numpy(),
    )


# ----------------------------------------------------------------------
# 1 dB compression point
# ----------------------------------------------------------------------

def calculate_p1db(input_power, gain):
    """
    Calculate the 1 dB compression point relative to maximum gain.

    Returns
    -------
    p1db_input : float
        RF input power at the 1 dB compression point (dBm).
    p1db_gain : float
        Gain at the 1 dB compression point (dB).
    max_gain : float
        Maximum simulated gain (dB).

    Returns None for the compression point if the gain never drops
    by at least 1 dB after reaching its maximum.
    """

    max_gain = np.max(gain)
    target_gain = max_gain - 1.0

    # Locate the maximum gain
    max_index = np.argmax(gain)

    # Search for the first crossing after the maximum gain
    for i in range(max_index + 1, len(gain)):

        if gain[i] <= target_gain:

            # Previous sample and current sample bracket the crossing
            x1, x2 = input_power[i - 1], input_power[i]
            y1, y2 = gain[i - 1], gain[i]

            # Linear interpolation
            if y2 == y1:
                p1db_input = x2
            else:
                p1db_input = x1 + (
                    (target_gain - y1)
                    * (x2 - x1)
                    / (y2 - y1)
                )

            return p1db_input, target_gain, max_gain

    # No 1 dB compression point found
    return None, None, max_gain


# ----------------------------------------------------------------------
# Plot
# ----------------------------------------------------------------------

fig, ax = plt.subplots()

for label, filepath in DATASETS.items():

    if not filepath.is_file():
        raise FileNotFoundError(
            f"Could not find CSV file: {filepath}"
        )

    input_power, gain = load_gain_data(filepath)

    # Calculate P1dB
    p1db_input, p1db_gain, max_gain = calculate_p1db(
        input_power,
        gain,
    )

    # Plot gain curve
    ax.plot(
        input_power,
        gain,
        color=COLORS[label],
        label=(
            f"{label} "
            f"($G_{{\\mathrm{{P1dB}}}} = {p1db_gain:.2f}\\,\\mathrm{{dB}}$)"
            if p1db_gain is not None
            else f"{label} ($P_{{1\\mathrm{{dB}}}}$ not reached)"
        ),
    )

    # # Mark P1dB with a vertical dashed line
    # if p1db_input is not None:
    #     ax.axvline(
    #         p1db_input,
    #         color=COLORS[label],
    #         linestyle="--",
    #         linewidth=1.2,
    #         alpha=0.8,
    #     )

    # Mark the P1dB operating point
    if p1db_input is not None:

        ax.plot(
            p1db_input,
            p1db_gain,
            marker="x",
            color=COLORS[label],
            markersize=8,
            markeredgewidth=2,
            linestyle="none",
            zorder=5,
        )

    # Maximum gain reference
    ax.axhline(
        max_gain,
        color=COLORS[label],
        linestyle=":",
        linewidth=1.0,
        alpha=0.7,
    )


# ----------------------------------------------------------------------
# Formatting
# ----------------------------------------------------------------------

ax.set_xlabel("RF input power (dBm)")
ax.set_ylabel("Gain (dB)")

ax.legend()
ax.grid(True, alpha=0.3)

fig.tight_layout()
plt.show()