import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'modules')))

import argparse
import csv
from pathlib import Path

from modules.util_parser import parse_TD_tecplot
import modules.util_utils as utils

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
class UI:
    path_to_file = ""
    filename_base = "Xyce_script_nested_param_hb_playground"
    filename_ext = ".txt.HB.TD.dat"
    save_path = ""

    params = {
        "Example": "Value"
    }

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
def build_header(variables, datasets):
    if not datasets:
        return variables

    header = []

    # First column = TIME
    header.append(variables[0])

    # Swept parameters
    header.extend(datasets[0]["params"].keys())

    # Remaining variables
    header.extend(variables[1:])

    return header

# ------------------------------------------------------------
# Rows
# ------------------------------------------------------------
def build_rows(datasets):
    rows = []
    for dataset in datasets:
        params = list(dataset["params"].values())

        for point in dataset["data"]:

            row = []

            # Time
            row.append(point[0])

            # Parameter values
            row.extend(params)

            # Remaining signals
            row.extend(point[1:])

            rows.append(row)

    return rows


# ------------------------------------------------------------
# Filename
# ------------------------------------------------------------
def build_filename(base, params):
    if len(params) == 0:
        return base + ".csv"

    param_string = "_".join(f"{k}-{v}" for k, v in params.items())

    return f"{base}_{param_string}_TD.csv"

def get_path_filename_TD(args=None) -> Path:
    ui = UI()

    # if this is an external call, transfer inputs to the ui
    if isinstance(args, dict):
        utils.transfer_args_to_ui(args, ui)

    out = Path(ui.save_path) / Path(build_filename(ui.filename_base, ui.params))

    # TODO: check if location exists

    return out


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def save_tecplot_TD_as_csv(args=None) -> Path:
    ui = UI()

    # if this is an external call, transfer inputs to the ui
    if isinstance(args, dict):
        utils.transfer_args_to_ui(args, ui)

    # Check if file is present
    if not Path(ui.path_to_file / (ui.filename_base + ui.filename_ext)).exists():
        raise FileNotFoundError(f"Input file not found: {ui.path_to_file / (ui.filename_base + ui.filename_ext)}")

    # Conversion
    variables, datasets = parse_TD_tecplot(ui.path_to_file / (ui.filename_base + ui.filename_ext))

    header = build_header(variables, datasets)
    rows = build_rows(datasets)

    output_filename = build_filename(ui.filename_base, ui.params)
    if ui.save_path:
        os.makedirs(ui.save_path, exist_ok=True)
        output_filename = ui.save_path / output_filename

    with open(output_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    return Path(output_filename)

if __name__ == "__main__":
    res = save_tecplot_TD_as_csv()