import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'modules')))

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import EngFormatter
from tqdm import tqdm

import modules.util_utils as utils
import modules.util_plotter as plotter
# ============================================================
# Configuration
# ============================================================

class UI:
    def __init__(self):
        self.path_to_file = "../data/2026-07-14_test/"
        self.csv_file = "Xyce_script_nested_param_hb_playground_C4-1uF_Rload-1-50_Ibase_pp-2.3uA_Icc_pp-3.11mA_fundamental-24GHz_TD.csv"
        self.save_path = self.path_to_file + "figs/TD/"

        # Which signal(s) to plot
        self.y_variables = [
            "ALL"
            # "V(VOUT)",
        ]

        self.x_variable = "TIME"

        # Value used for a single parameter sweep
        self.parameter_value = None
    
        # Initial the path to Path objects
        utils.init_paths(self)



# ============================================================
# Read CSV
# ============================================================
def load_csv(filename):
    return pd.read_csv(filename)


# ============================================================
# Sweep Detection
# ============================================================
def detect_sweep_structure(df):
    """
    Returns

        no_sweep
        single_sweep
        nested_sweep

    together with the parameter columns.
    """
    parameter_columns = []

    for col in df.columns:
        if col.upper() != "TIME" and not col.startswith(("V(V", "I(V")):
            parameter_columns.append(col)

    if len(parameter_columns) == 0:
        return "no_sweep", parameter_columns

    if len(parameter_columns) == 1:
        return "single_sweep", parameter_columns

    return "nested_sweep", parameter_columns


# ============================================================
# No Sweep
# ============================================================
def plot_no_sweep(df, ui):

    plotter.plot_TD_signals([df], ui)

# ============================================================
# Single Sweep
# ============================================================
def plot_single_sweep(df, parameter, ui):
    available = df[parameter].unique()

    parameter_values = select_parameter_value(
        available,
        parameter
    )

    # print(parameter_values)
    subsets = [] # Will contain a list of df
    for val in parameter_values:
        subsets.append(df[df[parameter] == val])
    # print(subsets[0])

    # print()
    # print(f"Plotting {parameter} = {parameter_values}")

    plotter.plot_TD_signals(
        subsets,
        ui
    )


# ============================================================
# Nested Sweep
# ============================================================
def plot_nested_sweep(df, parameter_columns, ui):

    print("Nested parameter sweeps are not implemented yet.")
    print(parameter_columns)

def print_values(values, max_cols=5):
    for index, value in enumerate(values):
        print(f"[{index:3d}] {value:<12g}", end="")

        if (index + 1) % max_cols == 0:
            print()

    # Finish the last line if it wasn't complete
    if len(values) % max_cols != 0:
        print()

def select_parameter_value(values, parameter_name) -> list:
    """
    Interactive selection of a parameter value.

    Returns the selected value.
    """

    values = sorted(values)

    print()
    print(f"Available values for {parameter_name}:")
    print("----------------------------------")

    print_values(values, max_cols=5)

    print()

    while True:

        try:
            selection_start = int(
                input("Select start of range to plot: ")
            )
            selection_end = int(
                input("Select end of range to plot: ")
            )

            if (0 <= selection_start < len(values) and
                0 <= selection_end < len(values) and
                selection_start <= selection_end):
                return values[selection_start:selection_end+1]

            else:
                print("Invalid indices.")

        except ValueError:
            print("Please enter an integer.")

# ============================================================
# Main
# ============================================================
def plot_TD(args=None):

    ui = UI()

    # if this is an external call, transfer inputs to the ui
    if isinstance(args, dict):
        print("External Call!")
        utils.transfer_args_to_ui(args, ui)

    print(ui.path_to_file)
    print(ui.csv_file)

    df = load_csv(ui.path_to_file / ui.csv_file)

    sweep_type, parameter_columns = detect_sweep_structure(df)
    print("Detected:", sweep_type)

    # Ensure the output directory exists
    ui.save_path.mkdir(parents=True, exist_ok=True)

    if sweep_type == "no_sweep":
        plot_no_sweep(df, ui)

    elif sweep_type == "single_sweep":
        plot_single_sweep(df, parameter_columns[0], ui)

    else:
        plot_nested_sweep(df, parameter_columns, ui)


if __name__ == "__main__":
    plot_TD()