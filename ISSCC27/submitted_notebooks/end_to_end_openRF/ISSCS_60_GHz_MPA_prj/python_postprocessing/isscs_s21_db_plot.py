from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Apply custom Matplotlib style
plt.style.use(Path(__file__).parent / "own.mplstyle")


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# Paths to data
DATASETS = {
    "Pre-EM":          Path("/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/02_preEM_60GHz_MPA_ngspice/s21_db.csv"),
    # "Post-EM":         Path("/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/03_postEM_60GHz_MPA_ngspice/s21_db.csv"),
}

TARGET_FREQ = 60e9  # 60 GHz

# Meaningful colors for the three configurations
COLORS = {
    "Pre-EM":          "tab:orange",
    "Post-EM":         "tab:green",
}


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def load_s21(filepath):
    """Load S21 data from a Qucs-S CSV export."""

    # The file uses semicolons as delimiters and has a header
    # containing quoted column names.
    df = pd.read_csv(
        filepath,
        sep=";",
        quotechar='"',
        skipinitialspace=True,
    )

    # Remove quotation marks and whitespace from column names
    df.columns = df.columns.str.replace('"', '', regex=False).str.strip()

    # Extract frequency and real part of S21 in dB
    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    s21_db = pd.to_numeric(df.iloc[:, 1], errors="coerce")

    # Remove invalid rows
    valid = freq.notna() & s21_db.notna()
    freq = freq[valid].to_numpy()
    s21_db = s21_db[valid].to_numpy()

    # Sort by frequency
    order = np.argsort(freq)

    return freq[order], s21_db[order]


# ----------------------------------------------------------------------
# Plot
# ----------------------------------------------------------------------

fig, ax = plt.subplots()

for label, filepath in DATASETS.items():

    if not filepath.is_file():
        raise FileNotFoundError(f"Could not find CSV file: {filepath}")

    freq, s21_db = load_s21(filepath)

    # Convert frequency to GHz for the x-axis
    freq_ghz = freq / 1e9

    # Interpolate the S11 value at 60 GHz
    if not (freq.min() <= TARGET_FREQ <= freq.max()):
        raise ValueError(
            f"{filepath}: 60 GHz is outside the available frequency "
            f"range ({freq.min()/1e9:.2f}–{freq.max()/1e9:.2f} GHz)."
        )

    s11_at_60ghz = np.interp(TARGET_FREQ, freq, s21_db)

    # Plot curve with the 60 GHz value in the legend
    ax.plot(
        freq_ghz,
        s21_db,
        color=COLORS[label],
        label=f"{label} ($S_{{21}}(60\\,\\mathrm{{GHz}})"
              f" = {s11_at_60ghz:.2f}\\,\\mathrm{{dB}}$)",
    )

    # Vertical dashed line at 60 GHz
    ax.axvline(
        x=TARGET_FREQ / 1e9,
        color="grey",
        linestyle="--",
        linewidth=1.0,
        alpha=0.8,
        zorder=0,
    )

# Axis labels
ax.set_xlabel("Frequency (GHz)")
ax.set_ylabel(r"$S_{21}$ (dB)")

# Legend
ax.legend()

# Optional grid
ax.grid(True, alpha=0.3)

fig.tight_layout()

plt.show()