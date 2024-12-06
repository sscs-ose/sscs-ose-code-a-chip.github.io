import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter


def plot_metrics(VG, GMs, BWs, IRNs, Ps, start, end):
    VG_linear = VG[start:end + 1]
    GMs_linear = GMs[start:end + 1]
    BWs_linear = BWs[start:end + 1]
    IRNs_linear = IRNs[start:end + 1]
    Ps_linear = Ps[start:end + 1]

    fig, axs = plt.subplots(2, 2)

    axs[0, 0].plot(VG, GMs*1000, label="full region")
    axs[0, 0].plot(VG_linear, GMs_linear*1000, label="linear region", color="red")
    axs[0, 0].set_title("Gm vs Vg")
    axs[0, 0].set_ylabel("Gm (mS)")
    axs[0, 0].yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    axs[0, 0].grid()

    axs[0, 1].plot(VG, BWs/1e6)
    axs[0, 1].plot(VG_linear, BWs_linear/1e6, color="red")
    axs[0, 1].set_title("BW vs Vg")
    axs[0, 1].set_ylabel("BW (MHz)")
    axs[0, 1].yaxis.set_major_formatter(FormatStrFormatter('%d'))
    axs[0, 1].grid()

    axs[1, 0].plot(VG, IRNs)
    axs[1, 0].plot(VG_linear, IRNs_linear, color="red")
    axs[1, 0].set_title("IRN vs Vg")
    axs[1, 0].set_ylabel("IRN (V/sqrt(Hz))")
    axs[1, 0].set_xlabel("Vg (V)")
    axs[1, 0].grid()

    axs[1, 1].plot(VG, Ps*1e3)
    axs[1, 1].plot(VG_linear, Ps_linear*1e3, color="red")
    axs[1, 1].set_title("Power vs Vg")
    axs[1, 1].set_ylabel("Power (mW)")
    axs[1, 1].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    axs[1, 1].set_xlabel("Vg (V)")
    axs[1, 1].grid()

    fig.legend(loc="lower center", fontsize="small")
    fig.tight_layout()
    plt.show()