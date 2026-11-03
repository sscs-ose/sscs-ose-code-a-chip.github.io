#!/usr/bin/env python3

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import skrf as rf

plt.style.use(Path(__file__).parent / "../python_postprocessing/own.mplstyle")


def dB(x):
    return 20 * np.log10(np.abs(x))


def main():

    parser = argparse.ArgumentParser(
        description="Postprocess a Touchstone .s2p file of an inductor."
    )

    parser.add_argument(
        "s2p",
        nargs="?",
        # default="/Users/matthi/IHP-PDK/sscs-ose-code-a-chip.github.io/ISSCC27/submitted_notebooks/end_to_end_openRF/ISSCS_60_GHz_MPA_prj/openEMS/output/run_VCC_snake_v6_data/run_VCC_snake_v6.s2p",
        default="/Users/matthi/IHP-PDK/sscs-ose-code-a-chip.github.io/ISSCC27/submitted_notebooks/end_to_end_openRF/ISSCS_60_GHz_MPA_prj/openEMS/output/run_Basebias_inductor_data/run_Basebias_inductor.s2p",
        help="Input Touchstone file (.s2p)"
    )

    parser.add_argument(
        "--target",
        type=float,
        default=60.0,
        help="Target frequency in GHz"
    )

    args = parser.parse_args()

    s2p_path = Path(args.s2p)

    if not s2p_path.exists():
        raise FileNotFoundError(s2p_path)

    print(f"Reading {s2p_path}")

    network = rf.Network(str(s2p_path))

    f = network.f
    s = network.s

    s11 = s[:, 0, 0]
    s21 = s[:, 1, 0]
    s12 = s[:, 0, 1]
    s22 = s[:, 1, 1]

    print(dB(s11[0]))

    # Convert S -> Z
    z = network.z

    z11 = z[:, 0, 0]
    z12 = z[:, 0, 1]
    z21 = z[:, 1, 0]
    z22 = z[:, 1, 1]

    omega = 2 * np.pi * f

    with np.errstate(divide="ignore", invalid="ignore"):
        zdiff = z11 - z12 - z21 + z22

        Ldiff = zdiff.imag / omega
        Rdiff = zdiff.real
        Qdiff = zdiff.imag / zdiff.real

    targetfreq = args.target * 1e9
    idx = np.argmax(f >= targetfreq)

    print(Ldiff[0])
    print(Ldiff[1])

    print("\nDifferential inductor parameters")
    print("--------------------------------")
    print(f"Frequency [GHz]: {f[idx]/1e9}")
    print(f"Series L  [nH] : {Ldiff[idx]*1e9}")
    print(f"Series R  [Ohm]: {Rdiff[idx]}")
    print(f"Q factor       : {Qdiff[idx]}")
    print("--------------------------------")
    print(f"L_DC      [nH] : {Ldiff[1]*1e9}")
    print(f"R_DC      [Ohm]: {Rdiff[0]}")
    print(f"Peak Q         : {np.nanmax(Qdiff)}")

    # ------------------------------------------------------------
    # Save CSV
    # ------------------------------------------------------------

    csv_file = s2p_path.with_name(s2p_path.stem + "_results.csv")
    print(s2p_path.stem + "_results.csv")

    df = pd.DataFrame({
        "Frequency (GHz)": f / 1e9,
        "Ldiff (nH)": Ldiff * 1e9,
        "Rdiff (Ohm)": Rdiff,
        "Qdiff": Qdiff,
        "S11 (dB)": dB(s11),
        "S21 (dB)": dB(s21),
        "S12 (dB)": dB(s12),
        "S22 (dB)": dB(s22),
    })

    df.to_csv(csv_file, index=False)

    print(f"\nResults written to {csv_file}")

    # ------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------

    output_dir = s2p_path.parent

    plt.figure("Return Loss", figsize=(7, 4))
    plt.plot(f / 1e9, dB(s11), label="S11")
    plt.plot(f / 1e9, dB(s22), "--", label="S22")
    plt.grid(True)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("Magnitude (dB)")
    plt.title("Return Loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "return_loss.png", dpi=300)

    plt.figure("Insertion Loss", figsize=(7, 4))
    plt.plot(f / 1e9, dB(s21), label="S21")
    plt.plot(f / 1e9, dB(s12), "--", label="S12")
    plt.grid(True)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("Magnitude (dB)")
    plt.title("Insertion Loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "insertion_loss.png", dpi=300)

    plt.figure("Inductance", figsize=(7, 4))
    plt.plot(f / 1e9, Ldiff * 1e9)
    plt.grid(True)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("L (nH)")
    plt.title("Differential Inductance")
    plt.tight_layout()
    plt.savefig(output_dir / "inductance.png", dpi=300)

    plt.figure("Q Factor", figsize=(7, 4))
    plt.plot(f / 1e9, Qdiff)
    plt.grid(True)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("Q")
    plt.title("Differential Q Factor")
    plt.tight_layout()
    plt.savefig(output_dir / "q_factor.png", dpi=300)


    # ------------------------------------------------------------
    # Combined Inductance and Q-Factor Plot
    # ------------------------------------------------------------

    fig, ax1 = plt.subplots(
        num="Inductance and Q Factor",
        figsize=(7, 4)
    )

    frequency_ghz = f / 1e9

    # Find the frequency point closest to 60 GHz
    target_freq_ghz = 60.0
    idx_60ghz = np.argmin(np.abs(frequency_ghz - target_freq_ghz))

    L_60ghz = Ldiff[idx_60ghz] * 1e9
    Q_60ghz = Qdiff[idx_60ghz]
    actual_freq_ghz = frequency_ghz[idx_60ghz]

    # Left y-axis: Inductance
    line1, = ax1.plot(
        frequency_ghz,
        Ldiff * 1e9,
        label=f"Inductance ({L_60ghz:.3f} nH @ {actual_freq_ghz:.2f} GHz)",
    )

    ax1.set_xlabel("Frequency (GHz)")
    ax1.set_ylabel("Inductance (nH)")
    ax1.grid(True)

    # Right y-axis: Q-factor
    ax2 = ax1.twinx()

    line2, = ax2.plot(
        frequency_ghz,
        Qdiff,
        color='red',
        label=f"Q-factor ({Q_60ghz:.2f} @ {actual_freq_ghz:.2f} GHz)",
    )

    ax2.set_ylabel("Q-factor")

    # Combined legend for both y-axes
    ax1.legend(
        [line1, line2],
        [line1.get_label(), line2.get_label()],
        loc="best",
        framealpha=1.0,
    )

    ax1.set_title("Differential Inductance and Q-Factor")

    fig.tight_layout()
    fig.savefig(
        output_dir / "inductance_q_factor.png",
        dpi=300,
    )


    # plt.show()


if __name__ == "__main__":
    main()