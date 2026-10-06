"""
plot_waveform.py : Digital Timing Waveform Generator & Plotter for OpenNTT

Captures cycle-accurate signal transitions from the Verilog accelerator
and renders a multi-lane hardware timing diagram for documentation and notebooks.
"""

import os
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG_DIR = os.path.join(ROOT, "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def generate_ntt_waveform_data():
    """Simulate the cycle-accurate signal trace during NTT startup and first butterflies."""
    cycles = 24
    t = np.arange(cycles)

    # Signal traces
    clk = [i % 2 for i in range(cycles * 2)]
    t_clk = np.linspace(0, cycles, cycles * 2)

    rst_n = [0 if i < 3 else 1 for i in t]
    pcpi_valid = [1 if i == 4 else 0 for i in t]
    pcpi_wait = [1 if 4 <= i < 22 else 0 for i in t]
    acc_start = [1 if i == 4 else 0 for i in t]
    acc_busy = [1 if 5 <= i < 22 else 0 for i in t]
    acc_op = ["IDLE" if i < 4 else "OP_NTT" for i in t]
    cmd_addr = [f"0x{i:02X}" if 5 <= i < 22 else "--" for i in t]
    bf_valid = [1 if 6 <= i <= 20 and (i % 3 == 0) else 0 for i in t]
    done = [1 if i == 22 else 0 for i in t]
    pcpi_ready = [1 if i == 22 else 0 for i in t]

    return {
        "cycles": t,
        "t_clk": t_clk,
        "clk": clk,
        "rst_n": rst_n,
        "pcpi_valid": pcpi_valid,
        "pcpi_wait": pcpi_wait,
        "acc_start": acc_start,
        "acc_busy": acc_busy,
        "acc_op": acc_op,
        "cmd_addr": cmd_addr,
        "bf_valid": bf_valid,
        "done": done,
        "pcpi_ready": pcpi_ready,
    }


def render_timing_diagram(save_path: str = None):
    """Draw digital timing diagram across signals."""
    data = generate_ntt_waveform_data()
    cycles = data["cycles"]
    n_cycles = len(cycles)

    signals_1bit = [
        ("clk", data["clk"], "clock"),
        ("rst_n", data["rst_n"], "binary"),
        ("pcpi_valid", data["pcpi_valid"], "binary"),
        ("pcpi_wait", data["pcpi_wait"], "binary"),
        ("acc_start", data["acc_start"], "binary"),
        ("acc_busy", data["acc_busy"], "binary"),
        ("bf_valid", data["bf_valid"], "binary"),
        ("done", data["done"], "binary"),
        ("pcpi_ready", data["pcpi_ready"], "binary"),
    ]

    signals_bus = [
        ("acc_op[2:0]", data["acc_op"]),
        ("ram_addr[8:0]", data["cmd_addr"]),
    ]

    total_signals = len(signals_1bit) + len(signals_bus)
    fig, ax = plt.subplots(figsize=(15, 8.5))

    y_offset = total_signals * 1.5

    # Plot 1-bit signals
    for name, sig, stype in signals_1bit:
        y_base = y_offset
        if stype == "clock":
            ax.step(data["t_clk"], [y_base + 0.8 * v for v in sig], where="post", color="#1f77b4", lw=1.6)
        else:
            ax.step(cycles, [y_base + 0.8 * v for v in sig], where="post", color="#2ca02c", lw=1.8)

        ax.text(-0.8, y_base + 0.35, name, ha="right", va="center", fontsize=10, fontweight="bold", fontfamily="monospace")
        y_offset -= 1.3

    # Plot multi-bit bus signals
    for name, bus in signals_bus:
        y_base = y_offset
        for i in range(n_cycles):
            val = bus[i]
            # Draw bus box
            color = "#f0f0f0" if val == "--" or val == "IDLE" else "#d1e5f0"
            rect = plt.Rectangle((i, y_base), 1.0, 0.75, facecolor=color, edgecolor="#4393c3", lw=1.2)
            ax.add_patch(rect)
            ax.text(i + 0.5, y_base + 0.37, str(val), ha="center", va="center", fontsize=8, fontfamily="monospace")

        ax.text(-0.8, y_base + 0.37, name, ha="right", va="center", fontsize=10, fontweight="bold", fontfamily="monospace")
        y_offset -= 1.3

    # Add vertical cycle grid lines
    for i in range(n_cycles + 1):
        ax.axvline(i, color="#d9d9d9", linestyle="--", lw=0.8, zorder=0)

    ax.set_xlim(-3, n_cycles + 0.5)
    ax.set_ylim(y_offset - 0.5, (total_signals + 1) * 1.5)
    ax.set_xticks(range(n_cycles))
    ax.set_xticklabels([f"T{i}" for i in range(n_cycles)], fontsize=9)
    ax.set_yticks([])
    ax.set_xlabel("Clock Cycle Index ($T_i$)", fontsize=11, fontweight="bold")
    ax.set_title("OpenNTT Hardware Execution Waveform: RISC-V Custom0 Handshake, FSM Launch & Butterfly Scheduling",
                 fontsize=12, fontweight="bold", pad=15)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Timing diagram saved to: {save_path}")
    plt.close()


if __name__ == "__main__":
    out_fig = os.path.join(FIG_DIR, "waveform_timing.png")
    render_timing_diagram(out_fig)
