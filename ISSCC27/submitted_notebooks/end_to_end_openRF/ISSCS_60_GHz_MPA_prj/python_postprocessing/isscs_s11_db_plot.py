# from pathlib import Path

# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt

# # Apply custom Matplotlib style
# plt.style.use(Path(__file__).parent / "own.mplstyle")


# # ----------------------------------------------------------------------
# # Configuration
# # ----------------------------------------------------------------------

# # Paths to data
# DATASETS = {
#     "Pre-EM":          Path("/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/02_preEM_60GHz_MPA_ngspice/s11_db.csv"),
#     "Post-EM":         Path("/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/python_postprocessing/data/2026-10-27/03_postEM_60GHz_MPA_ngspice/s11_db.csv"),
# }

# TARGET_FREQ = 60e9  # 60 GHz

# # Meaningful colors for the three configurations
# COLORS = {
#     "Pre-EM":          "tab:orange",
#     "Post-EM":         "tab:green",
# }


# # ----------------------------------------------------------------------
# # Data loading
# # ----------------------------------------------------------------------

# def load_s11(filepath):
#     """Load S11 data from a Qucs-S CSV export."""

#     # The file uses semicolons as delimiters and has a header
#     # containing quoted column names.
#     df = pd.read_csv(
#         filepath,
#         sep=";",
#         quotechar='"',
#         skipinitialspace=True,
#     )

#     # Remove quotation marks and whitespace from column names
#     df.columns = df.columns.str.replace('"', '', regex=False).str.strip()

#     # Extract frequency and real part of S11 in dB
#     freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
#     s11_db = pd.to_numeric(df.iloc[:, 1], errors="coerce")

#     # Remove invalid rows
#     valid = freq.notna() & s11_db.notna()
#     freq = freq[valid].to_numpy()
#     s11_db = s11_db[valid].to_numpy()

#     # Sort by frequency
#     order = np.argsort(freq)

#     return freq[order], s11_db[order]


# # ----------------------------------------------------------------------
# # Plot
# # ----------------------------------------------------------------------

# fig, ax = plt.subplots()

# for label, filepath in DATASETS.items():

#     if not filepath.is_file():
#         raise FileNotFoundError(f"Could not find CSV file: {filepath}")

#     freq, s11_db = load_s11(filepath)

#     # Convert frequency to GHz for the x-axis
#     freq_ghz = freq / 1e9

#     # Interpolate the S11 value at 60 GHz
#     if not (freq.min() <= TARGET_FREQ <= freq.max()):
#         raise ValueError(
#             f"{filepath}: 60 GHz is outside the available frequency "
#             f"range ({freq.min()/1e9:.2f}–{freq.max()/1e9:.2f} GHz)."
#         )

#     s11_at_60ghz = np.interp(TARGET_FREQ, freq, s11_db)

#     # Plot curve with the 60 GHz value in the legend
#     ax.plot(
#         freq_ghz,
#         s11_db,
#         color=COLORS[label],
#         label=f"{label} ($S_{{11}}(60\\,\\mathrm{{GHz}})"
#               f" = {s11_at_60ghz:.2f}\\,\\mathrm{{dB}}$)",
#     )

#     # Vertical dashed line at 60 GHz
#     ax.axvline(
#         x=TARGET_FREQ / 1e9,
#         color="grey",
#         linestyle="--",
#         linewidth=1.0,
#         alpha=0.8,
#         zorder=0,
#     )

# ax.set_ylim(bottom=-30)

# # Axis labels
# ax.set_xlabel("Frequency (GHz)")
# ax.set_ylabel(r"$S_{11}$ (dB)")

# # Legend
# ax.legend()

# # Optional grid
# ax.grid(True, alpha=0.3)

# fig.tight_layout()

# plt.show()



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
        "/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/"
        "python_postprocessing/data/2026-10-27/"
        "02_preEM_60GHz_MPA_ngspice/s11_db.csv"
    ),
    "Post-EM": Path(
        "/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/"
        "python_postprocessing/data/2026-10-27/"
        "03_postEM_60GHz_MPA_ngspice/s11_db.csv"
    ),
}

TARGET_FREQ = 60e9  # 60 GHz
S11_THRESHOLD = -10  # dB

COLORS = {
    "Pre-EM": "tab:orange",
    "Post-EM": "tab:green",
}


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def load_s11(filepath):
    """Load S11 data from a Qucs-S CSV export."""

    df = pd.read_csv(
        filepath,
        sep=";",
        quotechar='"',
        skipinitialspace=True,
    )

    # Clean column names
    df.columns = df.columns.str.replace('"', "", regex=False).str.strip()

    # Extract frequency and S11 in dB
    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    s11_db = pd.to_numeric(df.iloc[:, 1], errors="coerce")

    # Remove invalid rows
    valid = freq.notna() & s11_db.notna()
    freq = freq[valid].to_numpy()
    s11_db = s11_db[valid].to_numpy()

    # Sort by frequency
    order = np.argsort(freq)

    return freq[order], s11_db[order]


# ----------------------------------------------------------------------
# Find frequency intervals below the S11 threshold
# ----------------------------------------------------------------------

def find_s11_intervals(freq, s11_db, threshold=-10):
    """Return contiguous frequency intervals where S11 is below threshold."""

    below = s11_db < threshold

    # Find the indices where the condition changes
    changes = np.diff(np.r_[False, below, False].astype(int))

    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0] - 1

    intervals = []

    for start, end in zip(starts, ends):
        f_start = freq[start]
        f_end = freq[end]

        # Interpolate threshold crossings for more accurate boundaries
        if start > 0:
            f_start = np.interp(
                threshold,
                [s11_db[start - 1], s11_db[start]],
                [freq[start - 1], freq[start]],
            )

        if end < len(s11_db) - 1:
            f_end = np.interp(
                threshold,
                [s11_db[end], s11_db[end + 1]],
                [freq[end], freq[end + 1]],
            )

        intervals.append((f_start / 1e9, f_end / 1e9))

    return intervals


# ----------------------------------------------------------------------
# Plot
# ----------------------------------------------------------------------

fig, ax = plt.subplots()

for label, filepath in DATASETS.items():

    if not filepath.is_file():
        raise FileNotFoundError(f"Could not find CSV file: {filepath}")

    freq, s11_db = load_s11(filepath)
    freq_ghz = freq / 1e9

    # Interpolate S11 at 60 GHz
    if not (freq.min() <= TARGET_FREQ <= freq.max()):
        raise ValueError(
            f"{filepath}: 60 GHz is outside the available frequency "
            f"range ({freq.min()/1e9:.2f}–{freq.max()/1e9:.2f} GHz)."
        )

    s11_at_60ghz = np.interp(TARGET_FREQ, freq, s11_db)

    # Find intervals below -10 dB
    intervals = find_s11_intervals(freq, s11_db, S11_THRESHOLD)

    if intervals:
        interval_text = ", ".join(
            f"{start:.2f}–{end:.2f} GHz"
            for start, end in intervals
        )
    else:
        interval_text = "none"

    # Plot the S11 curve and include the intervals in the legend
    ax.plot(
        freq_ghz,
        s11_db,
        color=COLORS[label],
        label=(
            f"{label} "
            f"($S_{{11}}(60\\,\\mathrm{{GHz}})"
            f" = {s11_at_60ghz:.2f}\\,\\mathrm{{dB}}$)"
            f"\n$S_{{11}} < -10\\,\\mathrm{{dB}}$: {interval_text}"
        ),
    )

    # Mark all points below -10 dB
    below = s11_db < S11_THRESHOLD

    ax.plot(
        freq_ghz[below],
        s11_db[below],
        linestyle="none",
        marker="o",
        markersize=3,
        color=COLORS[label],
        label="_nolegend_",
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

# Axis limits and labels
ax.set_ylim(bottom=-30)
ax.set_xlabel("Frequency (GHz)")
ax.set_ylabel(r"$S_{11}$ (dB)")

# Legend
ax.legend()

# Grid
ax.grid(True, alpha=0.3)

fig.tight_layout()
plt.show()