import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'modules')))

import argparse
import csv
from pathlib import Path

from modules.util_parser import parse_FD_tecplot
import modules.util_utils as utils

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
class UI:
    def __init__(self):
        self.path_to_file = ""
        self.filename_base = "Xyce_script_nested_param_hb_playground"
        self.filename_ext = ".txt.HB.FD.dat"
        self.save_path = ""
        self.params = {
            "C1": "5pF",
            "L1": "100pH",
            "C3": "1pF",}
        
        utils.init_paths(self)

# ------------------------------------------------------------
# Build Header
# ------------------------------------------------------------
def build_header(variables, datasets):
    if len(datasets) == 0:
        return variables

    param_names = list(datasets[0]["params"].keys())
    # print(param_names)

    header = []
    header.append(variables[0])              # Frequency
    header.extend(param_names)               # Innermost first
    header.extend(variables[1:])             # Measurements

    return header


# ------------------------------------------------------------
# Build Rows
# ------------------------------------------------------------
def build_rows(datasets):

    rows = []

    for dataset in datasets:
        params = list(dataset["params"].values())
        params = list(params)

        for point in dataset["data"]:
            row = []

            row.append(point[0])         # frequency
            row.extend(params)
            row.extend(point[1:])
            rows.append(row)

    return rows


# ------------------------------------------------------------
# Filename
# ------------------------------------------------------------
def build_filename(base, params):
    param_str = "_".join(f"{k}-{v}" for k, v in params.items())
    return f"{base}_{param_str}_FD.csv"


def get_path_filename_FD(args=None) -> Path:
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
def save_tecplot_FD_as_csv(args=None) -> Path:

    ui = UI()

    # if this is an external call, transfer inputs to the ui
    if isinstance(args, dict):
        utils.transfer_args_to_ui(args, ui)

    # Check if file is present
    if not Path(ui.path_to_file / (ui.filename_base + ui.filename_ext)).exists():
        raise FileNotFoundError(f"Input file not found: {ui.path_to_file / (ui.filename_base + ui.filename_ext)}")

    # Conversion
    variables, datasets = parse_FD_tecplot(ui.path_to_file / (ui.filename_base + ui.filename_ext))

    header = build_header(variables, datasets)
    rows = build_rows(datasets)

    # print(f"Variables : {len(variables)}")
    # print(f"Zones      : {len(datasets)}")

    output_filename = build_filename(ui.filename_base, ui.params)
    if ui.save_path != "":
        os.makedirs(ui.save_path, exist_ok=True)
        output_filename = ui.save_path / output_filename

    with open(output_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    # print(f"Wrote {len(rows)} rows")
    # print(output_filename)

    return Path(output_filename)


if __name__ == "__main__":
    save_tecplot_FD_as_csv()