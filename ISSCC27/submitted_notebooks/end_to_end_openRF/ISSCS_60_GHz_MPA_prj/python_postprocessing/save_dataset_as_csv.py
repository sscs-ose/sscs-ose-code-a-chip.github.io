import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'modules')))


import argparse
from posixpath import sep
import re
import csv
from itertools import product
from pathlib import Path
import math

from modules.util_parser import parse_dataset

# --- User Interface ---
class UI:
    path_to_file = "" # "../" , ""
    filename_base = "24GHz_inv_Class-F_efficiency" # 24GHz_inv_Class-F_efficiency_xyce_script , 24GHz_inv_Class-F_efficiency
    filename_ext = ".dat.xyce"
    save_path = "" # "../data/eff_sweep/"
    params = {
        "C1": "5pF",
        "L1": "100pH",
        "C3": "1pF",}

# --- Functions ---
def build_rows(indep_values, dep_vars, dep_data):
    # grid is a list of tuples, where each tuple is a combination of independent variable values, where the first independent variable changes fastest
    grid = list(product(*indep_values[::-1]))
    grid = [tuple(reversed(p)) for p in grid]
    # print(f"{grid}, type={type(grid)}")
    # print(len(grid))

    rows = []

    for i, point in enumerate(grid):
        row = list(point)
        # print(f"{row}, i={i}")

        for dep in dep_vars:
            val = dep_data[dep][i]
            # print(type(val))

            # If val is purely real or purely imaginary, only append the value
            if isinstance(val, complex):
                if dep.startswith("Re(") or dep.startswith("Im("):
                    row.append(val.real)
                else:
                    row.append(val)
            # else append the entire complex value
            else:
                row.append(val)

        rows.append(row)

    return rows


def build_header(indep_vars, dep_vars):
    header = list(indep_vars) + dep_vars
    return header


def build_filename(base, params):
    param_str = "_".join(f"{k}-{v}" for k, v in params.items())
    return f"{base}_{param_str}.csv"


def main():
    ui = UI()

    parser = argparse.ArgumentParser()
    parser.add_argument("path_to_file", nargs="?", help="Path to input_file")
    parser.add_argument("input_file", nargs="?", help="Path to dataset file")
    parser.add_argument("save_path", nargs="?", help="Path to folder where the output file should be saved")
    parser.add_argument("--params", nargs="*", help="key=value pairs")

    args = parser.parse_args()

    # --- File and path handling ---
    if args.path_to_file:
        path_to_file = args.path_to_file
    else:
        path_to_file = ui.path_to_file
    
    if args.input_file:
        filename = path_to_file + args.input_file
        left, sep, right = args.input_file.partition(".")
        right = sep + right
        filename_base = left
        filename_ext = sep + right
    else:
        filename = path_to_file + ui.filename_base + ui.filename_ext
        filename_base = ui.filename_base
        filename_ext = ui.filename_ext

    if not Path(filename).exists():
        raise FileNotFoundError(f"Input file not found: {filename}")
    
    if args.save_path:
        save_path = args.save_path
    else:
        save_path = ui.save_path

    # --- Parameter handling ---
    if args.params:
        params = dict(p.split("=") for p in args.params)
    else:
        params = ui.params

    output_filename = build_filename(filename_base, params)

    # --- Parse dataset ---
    indep_vars, indep_values, dep_vars, dep_data = parse_dataset(filename)
    # print(indep_vars)
    # print(indep_values)
    # print(dep_data)
    # for k, v in list(dep_data.items())[:2]:
    #     print(k, v)
    # print(dep_data["Re(I(VPR1))"])
    # print(dep_data["Im(I(VPR1))"])
    # print(dep_data["Re(I(VICOLLECTOR_IN))"])

    # --- Sanity check for the frequency values ---
    for i, val in enumerate(indep_vars):
        if val.lower() == 'freq':
            freq_vals = indep_values[i]
            break
    for freq in freq_vals:
        if freq != 0.0 and -freq not in freq_vals:
            print(f"WARNING: Did not find frequency {-freq} as opponent to {freq} in dataset. Maybe there were simulation errors!")

    # --- Sanity check that grid dimensions match indep_values dimension ---
    dims = []
    for dim in indep_values:
        dims.append(len(dim))
    target_dim = math.prod(dims)
    for k, v in list(dep_data.items()):
        lengh = len(v)
        if lengh != target_dim:
            print(f"WARNING: Amount of data for {k} ({lengh}) does not match expected dimension ({target_dim})!")

    # --- Build rows ---
    rows = build_rows(indep_values, dep_vars, dep_data)
    # print(len(rows))

    # --- Header ---
    header = build_header(indep_vars, dep_vars)

    # --- Write CSV ---
    if save_path != "":
        os.makedirs(save_path, exist_ok=True)  # Create folder if it doesn't exist
        output_filename = os.path.join(save_path, output_filename)

    with open(output_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"CSV written to: {output_filename}")


if __name__ == "__main__":
    main()