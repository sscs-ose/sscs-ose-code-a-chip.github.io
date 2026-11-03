from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Apply custom Matplotlib style
plt.style.use(Path(__file__).parent / "own.mplstyle")


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# Adapt these paths to your directory structure
DATASETS = {
    "Pre-EM":          Path("/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/02_preEM_60GHz_MPA_ngspice/k.csv"),
    "Post-EM":         Path("/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/03_postEM_60GHz_MPA_ngspice/k.csv"),
}

TARGET_FREQ = 60e9  # 60 GHz

# Consistent colors across plots
COLORS = {
    "Pre-EM":          "tab:orange",
    "Post-EM":         "tab:green",
}


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def load_k_factor(filepath):
    """Load the Rollet stability factor K from a Qucs-S CSV export."""

    df = pd.read_csv(
        filepath,
        sep=";",
        quotechar='"',
        skipinitialspace=True,
    )

    # Clean column names
    df.columns = (
        df.columns
        .str.replace('"', '', regex=False)
        .str.strip()
    )

    # Extract frequency and real component of K
    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    k_factor = pd.to_numeric(df.iloc[:, 1], errors="coerce")

    # Remove invalid rows
    valid = freq.notna() & k_factor.notna()
    freq = freq[valid].to_numpy()
    k_factor = k_factor[valid].to_numpy()

    # Sort by frequency
    order = np.argsort(freq)

    return freq[order], k_factor[order]


# ----------------------------------------------------------------------
# Plot
# ----------------------------------------------------------------------

fig, ax = plt.subplots()

for label, filepath in DATASETS.items():

    if not filepath.is_file():
        raise FileNotFoundError(
            f"Could not find CSV file: {filepath}"
        )

    freq, k_factor = load_k_factor(filepath)

    if len(freq) == 0:
        raise ValueError(f"No valid data found in {filepath}")

    # Convert frequency to GHz
    freq_ghz = freq / 1e9

    # Check whether 60 GHz lies within the data range
    if not (freq.min() <= TARGET_FREQ <= freq.max()):
        raise ValueError(
            f"{filepath}: 60 GHz is outside the available frequency "
            f"range ({freq.min()/1e9:.2f}–"
            f"{freq.max()/1e9:.2f} GHz)."
        )

    # Interpolate K at 60 GHz
    k_at_60ghz = np.interp(
        TARGET_FREQ,
        freq,
        k_factor,
    )

    # Plot curve and include K at 60 GHz in the legend
    ax.plot(
        freq_ghz,
        k_factor,
        color=COLORS[label],
        label=(
            f"{label} "
            f"($K(60\\,\\mathrm{{GHz}}) = "
            f"{k_at_60ghz:.2f}$)"
        ),
    )

# ----------------------------------------------------------------------
# Stability criterion
# ----------------------------------------------------------------------

ax.axhline(
    y=1,
    color="grey",
    linestyle="--",
    linewidth=1.2,
    alpha=0.8,
    label=r"Stability threshold ($K=1$)",
    zorder=0,
)

# ----------------------------------------------------------------------
# Formatting
# ----------------------------------------------------------------------

ax.set_xlabel("Frequency (GHz)")
ax.set_ylabel(r"Rollet stability factor $K$")

ax.set_ylim(bottom=0, top=5)

ax.legend()
ax.grid(True, alpha=0.3)

fig.tight_layout()
plt.show()