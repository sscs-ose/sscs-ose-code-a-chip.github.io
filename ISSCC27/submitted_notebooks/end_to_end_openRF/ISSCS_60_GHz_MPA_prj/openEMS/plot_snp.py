from pathlib import Path

import skrf as rf
import matplotlib.pyplot as plt
import numpy as np

file = "/Users/matthi/QucsWorkspace/60_GHz_MPA_prj/openEMS/output/run_BiasT_3dports_data/run_BiasT_3dports.s4p"

nw = rf.Network(file)

n_ports = nw.nports
freq = nw.f / 1e9

# Create n_ports x n_ports grid
fig, axes = plt.subplots(
    n_ports,
    n_ports,
    figsize=(12, 10),
    squeeze=False
)

for i in range(n_ports):
    for j in range(n_ports):
        ax = axes[i, j]

        # Magnitude
        magnitude = 20 * np.log10(np.abs(nw.s[:, i, j]))

        magnitude_line, = ax.plot(
            freq,
            magnitude,
            label="Magnitude"
        )

        magnitude_color = magnitude_line.get_color()

        ax.set_title(f"S{i+1}{j+1}")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Magnitude (dB)")
        ax.tick_params(axis="y", labelcolor=magnitude_color)
        ax.yaxis.label.set_color(magnitude_color)
        ax.grid(True)

        # Phase
        ax_phase = ax.twinx()

        # phase = np.angle(nw.s[:, i, j], deg=True) # -180 to +180
        phase = np.unwrap(np.angle(nw.s[:, i, j])) * 180 / np.pi # continous phase

        phase_line, = ax_phase.plot(
            freq,
            phase,
            color="tab:orange",
            label="Phase"
        )

        phase_color = phase_line.get_color()

        ax_phase.set_ylabel("Phase (°)")
        ax_phase.tick_params(axis="y", labelcolor=phase_color)
        ax_phase.yaxis.label.set_color(phase_color)

fig.suptitle(f"{n_ports}-port S-parameters", fontsize=14)
fig.tight_layout()

# Save picture
output_file = Path(file).with_suffix(".png")
fig.savefig(output_file, dpi=300, bbox_inches="tight")

plt.show()

print(f"Saved plot to: {output_file}")