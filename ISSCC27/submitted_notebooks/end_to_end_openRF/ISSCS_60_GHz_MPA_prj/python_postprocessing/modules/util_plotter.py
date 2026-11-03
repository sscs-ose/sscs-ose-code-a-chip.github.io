import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter
import matplotlib.offsetbox as offsetbox
import ipywidgets as widgets
from IPython.display import display
from tqdm import tqdm

from util_utils import *

# ============================================================
# Self-made Fourier Synthesis plot
# ============================================================
def fourier_real(freqs, mag, phase, t, upTo=-1, plot_harmonics=False):
    '''
    Computes the superposition of the real parts of a complex signal with magnitude and phase over time t
    '''
    x = np.full_like(t, mag[0], dtype=float)

    if upTo == -1:
        upTo = len(mag) - 1

    if plot_harmonics:
        n_plots = min(upTo, len(mag) - 1)

        fig, axes = plt.subplots(
            n_plots, 1,
            figsize=(8, 2*n_plots),
            sharex=True
        )

        if n_plots == 1:
            axes = [axes]

    plot_idx = 0

    for idx in range(1, len(mag)):
        if idx <= upTo:

            harmonic = mag[idx] * np.cos(
                2*np.pi*freqs[idx]*t + phase[idx]
            )

            # reconstruction
            x += harmonic

            # individual harmonic plot
            if plot_harmonics:
                axes[plot_idx].plot(t, harmonic)
                axes[plot_idx].set_title(
                    f"{idx}·f0, A={mag[idx]:.3e}"
                )
                # axes[plot_idx].grid(True)
                plot_idx += 1

    if plot_harmonics:
        axes[-1].set_xlabel("Time (s)")
        plt.tight_layout()
        plt.show()

    return x


def plot_fourier_synthesis(df, swept_params: dict, swept_param: str, ui):
    ''' Compose the fourier components from the HB analysis and create plots '''
    # Convert to upper letter
    ui.fourier_plot_var_list = [element.upper() for element in ui.fourier_plot_var_list]

    # Extract the fundamental
    f0 = np.nanmin(df[df['FREQ'] > 0]['FREQ'].values)
    print(f"f0={f0}")

    T0 = 1 / f0
    print(f"T0={T0}")

    # Time vector for one period
    t = np.linspace(0, 2*T0, 2000)

    # Extract all positive frequencies and DC
    freqs = []
    for freq in df['FREQ']:
        if freq in freqs:
            break
        elif freq not in freqs and freq >= 0.0:
            freqs.append(freq)
    print(f"freqs={freqs}")

    # Extract the data and put them into arrays
    df_plot = at_freqs(df, freqs)
    plot_dfs = [] # List of df which contain columns FREQ | PARAM | Mag | Phase
    for metric in ui.fourier_plot_var_list:
        keys = []
        for col in df_plot.columns:
            if ((metric+')' in col and (col.startswith("Mag(") or col.startswith("Phase("))) or
                col == "FREQ" or
                (not col.startswith('Re(') and not col.startswith('Im(') and not col.startswith('V(') and not col.startswith('I(') and not col.startswith("Mag(") and not col.startswith("Phase("))):
                keys.append(col)
        plot_dfs.append(df_plot[keys])

    # if n_max = -1, then all available harmonics will be used to reconstruct the signal
    # The highest harmonic is determined with n_max*f0
    n_max = -1
    for idx, metric in enumerate(ui.fourier_plot_var_list):
        if swept_params == {}:
            df_inst = plot_dfs[idx]
        else:
            # val='first' indicates that we use the first instance of a parameter sweep, if there is one
            df_inst = at_param(plot_dfs[idx], col='', val='last')
        
        # Create numpy arrays from the dataframes.
        col_freq = df_inst['FREQ'].to_numpy()
        col_mag = df_inst.loc[:, df_inst.columns.str.startswith('Mag(')].to_numpy().ravel()
        col_phase = df_inst.loc[:, df_inst.columns.str.startswith('Phase(')].to_numpy().ravel()

        # Compute the fourier synthesis
        x = fourier_real(col_freq, col_mag, col_phase, t, upTo=n_max)

        # Determine the unit for the axes
        if any('I(' in s for s in df_inst.columns):
            unitY = 'A'
        elif any('V(' in s for s in df_inst.columns):
            unitY = 'V'

        # Calculate values for the info box
        x_avg = f"Average={eng(np.mean(x))}{unitY}"
        x_max = f"Max={eng(np.max(x))}{unitY}"
        x_min = f"Min={eng(np.min(x))}{unitY}"
        harm_info = f"Highest harmonic={(min(n_max,len(col_freq)-1)) if n_max > -1 else len(col_freq)-1}*f0"
        info = '\n'.join((x_avg, x_max, x_min, harm_info))

        # plot
        fig, ax = plt.subplots()
        formatterX = EngFormatter(unit='s') # 'F' , 'H' , 'Ω' , 'dBm' , 'dB' , 'A' , 'V' , 's'
        formatterY = EngFormatter(unit=unitY) # 'F' , 'H' , 'Ω' , 'dBm' , 'dB' , 'A' , 'V' , 's'
        ax.xaxis.set_major_formatter(formatterX)
        ax.yaxis.set_major_formatter(formatterY)
        ax.plot(t, x, label='signal')

        ax.set_xlabel(f"Time")
        ax.set_ylabel("Amplitude")
        ax.set_title(f"{metric}")
        ax.legend(loc='upper right')

        ob = offsetbox.AnchoredText(info, loc="upper left")
        ob.patch.set(boxstyle='round', alpha=0.5)
        ax.add_artist(ob)

        plt.tight_layout()
        if ui.save_fourier_plots:
            plt.savefig(f"{ui.save_path}figs/{metric}_{write_params(select_params(ui.sch_params, ui.filename_params), sepIntra="-", sepInter="_")}_{swept_param}-{swept_params[swept_param]}.png")
        plt.show()


# ============================================================
# Xyce Time Domain data plot
# ============================================================
def plot_TD_signals(df_list, ui):

    # If first entry of y_variables is "ALL"
    temp_list = []

    y_variables = df_list[0].columns

    if ui.y_variables[0] == "ALL":

        for i in df_list[0].columns:

            if i.startswith(("V(V", "I(V")):
                temp_list.append(i)

        y_variables = temp_list

    for y in tqdm(y_variables, desc="Generating TD plots", unit="plot"):

        fig, ax = plt.subplots(figsize=(3.5, 2.625))

        # Determine the unit
        x_formatter = EngFormatter(find_unit(ui.x_variable))
        y_formatter = EngFormatter(find_unit(y))

        ax.xaxis.set_major_formatter(x_formatter)
        ax.yaxis.set_major_formatter(y_formatter)

        # Plot onto the plot for every df in df_list
        for df in df_list:

            # First compute the labels
            if is_param(df.columns[1]):
                label = f"{df.columns[1]}={df.iloc[1, 1]}{find_unit(df.columns[1])}"
            else:
                label = None

            if label is None:
                ax.plot(df[ui.x_variable], df[y])
            else:
                ax.plot(
                    df[ui.x_variable],
                    df[y],
                    label=label
                )

        ax.set_title(f"HB time domain data for {clean_item(y)}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Signal")

        handles, labels = ax.get_legend_handles_labels()

        if labels:
            if len(labels) > 3:
                ax.legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.20),
                    ncol=3
                )
            else:
                ax.legend()

        fig.savefig(
            ui.save_path / (clean_item(y) + ".png"),
        )

        plt.close(fig)



def plot_1p(df, swept_params, y_col, ylabel, title, out_name):
    fig, ax = plt.subplots()
    formatter = EngFormatter(unit=swept_params[next(iter(swept_params))]["unit"])
    ax.xaxis.set_major_formatter(formatter)
    ax.plot(df[next(iter(swept_params))].to_numpy(), df[y_col], marker='o')

    ax.set_xlabel(f"Parameter {next(iter(swept_params))}")
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    plt.tight_layout()
    plt.savefig(out_name)


def plot_2p(df, swept_params, z_col, title, out_name):
    # Determine the x and y params:
    xy_params = [k for k in swept_params]

    pivot = (
        df.pivot_table(
            index=xy_params[1],
            columns=xy_params[0],
            values=z_col,
            aggfunc="mean"
        )
        .sort_index()
        .sort_index(axis=1)
    )
    fig, ax = plt.subplots()
    # plt.close(fig)
    x = pivot.columns.to_numpy(float)
    y = pivot.index.to_numpy(float)
    z = pivot.to_numpy()

    x_edges = centers_to_edges(x)
    y_edges = centers_to_edges(y)

    mesh = ax.pcolormesh(
        x_edges,
        y_edges,
        z,
        shading="flat",
        cmap="viridis",
    )

    fig.colorbar(mesh, ax=ax, label=title)

    # Put ticks at the actual sweep values
    ax.set_xticks(x)
    ax.set_yticks(y)

    ax.xaxis.set_major_formatter(
        EngFormatter(unit=swept_params[xy_params[0]]["unit"])
    )
    ax.yaxis.set_major_formatter(
        EngFormatter(unit=swept_params[xy_params[1]]["unit"])
    )

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    ax.set_xlabel(f"{xy_params[0]}")
    ax.set_ylabel(f"{xy_params[1]}")
    ax.set_title(title)

    fig.tight_layout()
    plt.savefig(out_name)
    plt.show()

def centers_to_edges(c):
    c = np.asarray(c, dtype=float)

    if len(c) == 1:
        # arbitrary half-width for a single point
        return np.array([c[0] - 0.5, c[0] + 0.5])

    edges = np.empty(len(c) + 1)
    edges[1:-1] = (c[:-1] + c[1:]) / 2
    edges[0] = c[0] - (c[1] - c[0]) / 2
    edges[-1] = c[-1] + (c[-1] - c[-2]) / 2
    return edges

def plot_3p(df, swept_params, fixed_param, z_col, title):
    # Determine the x and y params:
    xy_params = [k for k in swept_params if k != fixed_param.upper()]

    slider_vals = sorted(df[fixed_param].unique())
    # print(slider_vals)

    slider = widgets.SelectionSlider(
        options=slider_vals,
        description=fixed_param,
        continuous_update=False,
        orientation='horizontal'
    )

    def plot_heatmap(**kwargs):
        fixed_value = kwargs[fixed_param]

        dff = df[df[fixed_param] == fixed_value]

        pivot = (
            dff.pivot_table(
                index=xy_params[1],
                columns=xy_params[0],
                values=z_col,
                aggfunc="mean"
            )
            .sort_index()
            .sort_index(axis=1)
        )
        fig, ax = plt.subplots()
        # plt.close(fig)
        x = pivot.columns.to_numpy(float)
        y = pivot.index.to_numpy(float)
        z = pivot.to_numpy()

        x_edges = centers_to_edges(x)
        y_edges = centers_to_edges(y)

        mesh = ax.pcolormesh(
            x_edges,
            y_edges,
            z,
            shading="flat",
            cmap="viridis",
        )

        fig.colorbar(mesh, ax=ax, label=title)

        # Put ticks at the actual sweep values
        ax.set_xticks(x)
        ax.set_yticks(y)

        ax.xaxis.set_major_formatter(
            EngFormatter(unit=swept_params[xy_params[0]]["unit"])
        )
        ax.yaxis.set_major_formatter(
            EngFormatter(unit=swept_params[xy_params[1]]["unit"])
        )

        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        ax.set_xlabel(f"{xy_params[0]}")
        ax.set_ylabel(f"{xy_params[1]}")
        ax.set_title(f"{title}\n{fixed_param} = {fixed_value:g}")

        fig.tight_layout()
        plt.show()

    out = widgets.interactive_output(
        plot_heatmap,
        {fixed_param: slider}
    )

    display(slider, out)

def plot_generic(
    x,
    y,
    title=None,
    xlabel=None,
    xunit=None,
    ylabel=None,
    yunit=None,
    label=None,
    show=True,
    save_path_filename=None,
):
    """
    Generic plotting function for x-y data.

    Parameters
    ----------
    x : array-like
        X-axis data.
    y : array-like
        Y-axis data.
    title : str, optional
        Plot title.
    xlabel : str, optional
        X-axis label.
    xunit : str, optional
        X-axis unit.
    ylabel : str, optional
        Y-axis label.
    yunit : str, optional
        Y-axis unit.
    label : str, optional
        Legend label for the plotted data.
    show : bool, optional
        Whether to display the plot.
    save_path_filename : str or Path, optional
        Full path including filename and extension for saving the figure.
    """

    # fig, ax = plt.subplots(figsize=(3.5, 2.625))
    fig, ax = plt.subplots()

    # Set unit if specified
    if xunit:
        xformatter = EngFormatter(unit=xunit)
        ax.xaxis.set_major_formatter(xformatter)
    if yunit:
        yformatter = EngFormatter(unit=yunit)
        ax.yaxis.set_major_formatter(yformatter)

    # Plot data
    if label is not None:
        ax.plot(x, y, label=label)
        ax.legend()
    else:
        ax.plot(x, y)

    # Labels and title
    if title is not None:
        ax.set_title(title)

    if xlabel is not None:
        ax.set_xlabel(xlabel)

    if ylabel is not None:
        ax.set_ylabel(ylabel)

    # Save figure
    if save_path_filename is not None:
        save_path_filename = Path(save_path_filename)
        save_path_filename.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path_filename)

    # Show or close
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_compression(
    x,
    y,
    title=None,
    xlabel=None,
    xunit=None,
    ylabel=None,
    yunit=None,
    show=True,
    save_path_filename=None,
):
    """
    Compression point plot. Gain over RF input power

    Parameters
    ----------
    x : array-like
        X-axis data.
    y : array-like
        Y-axis data.
    title : str, optional
        Plot title.
    xlabel : str, optional
        X-axis label.
    xunit : str, optional
        X-axis unit.
    ylabel : str, optional
        Y-axis label.
    yunit : str, optional
        Y-axis unit.
    show : bool, optional
        Whether to display the plot.
    save_path_filename : str or Path, optional
        Full path including filename and extension for saving the figure.
    """

    # fig, ax = plt.subplots(figsize=(3.5, 2.625))
    fig, ax = plt.subplots()

    # Set unit if specified
    if xunit:
        xformatter = EngFormatter(unit=xunit)
        ax.xaxis.set_major_formatter(xformatter)
    if yunit:
        yformatter = EngFormatter(unit=yunit)
        ax.yaxis.set_major_formatter(yformatter)

    # Calculate compression point
    max_gain = y.max()

    for index, value in enumerate(y.values):
        diff = max_gain - value
        if diff > 1:
            P1db_index = index
            P1db = value
            break

    try:
        ax.axvline(x[P1db_index], color="red", linestyle="--", label=f"P1dB = {P1db:.2f} dB")
    except:
        print("Could not determine compression point!")

    ax.axhline(max_gain, color="blue", linestyle="--", label=f"Max Gain = {max_gain:.2f} dB")

    # Plot data
    ax.plot(x, y, label=f"Gain")
    ax.legend()


    # Labels and title
    if title is not None:
        ax.set_title(title)

    if xlabel is not None:
        ax.set_xlabel(xlabel)

    if ylabel is not None:
        ax.set_ylabel(ylabel)

    # Save figure
    if save_path_filename is not None:
        save_path_filename = Path(save_path_filename)
        save_path_filename.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path_filename)

    # Show or close
    if show:
        plt.show()
    else:
        plt.close(fig)
