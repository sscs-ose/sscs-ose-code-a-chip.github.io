# %%
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'modules')))

from pathlib import Path
import pandas as pd
pd.set_option('display.float_format', lambda x: '%.22f' % x)
import numpy as np
import matplotlib.pyplot as plt
plt.style.use(Path(__file__).parent / "own.mplstyle")
from matplotlib.ticker import EngFormatter
import matplotlib.offsetbox as offsetbox

from datetime import datetime

import modules.util_plotter as plotter
import modules.util_utils as utils
import modules.util_parser as parser

from save_tecplot_TD_as_csv import save_tecplot_TD_as_csv, get_path_filename_TD
from save_tecplot_FD_as_csv import save_tecplot_FD_as_csv, get_path_filename_FD
from plot_TD import plot_TD

######################
### USER INTERFACE ###
######################

class UI:
    def __init__(self):
        self.path_to_file = "../" # "../" , ""
        self.filename_base = "03_postEM_60GHz_MPA_xyce" # 01_initial_50GHz_MPA_xyce
        self.filename_ext_FD = ".txt.HB.FD.dat" # .dat.xyce , .txt.HB.FD.dat
        self.filename_ext_TD = ".txt.HB.TD.dat"

        self.read_orig_data = True # True: read the .txt.HB.XD.dat files | False: Operate on the already read-in csv files under data/
        self.converter_script_FD = "save_tecplot_FD_as_csv.py"
        self.converter_script_TD = "save_tecplot_TD_as_csv.py"

        self.save_path = f"data/{datetime.now().strftime("%Y-%m-%d")}/{datetime.now().strftime("%H-%M-%S")}_03_postEM_60GHz_MPA_xyce/"
        self.td_plot_script = "time_domain_plot.py"
        self.fd_plot_script = "frequency_domain_plot.py" # TODO implementation needed
        self.td_plot_save_path = Path(self.save_path + "figs/TD")

        
        self.fundamental = 60e9 # TODO automate from input data
        self.filename_params = [  # Order matters! filename_params are only here to build a unique filename for that simulation.
            "fundamental",
            "Irf_in"
        ]

        self.sch_params = {} # This will contain a dict of all components, sources and parameters on the schematic that are activated. Parameter sweeps will be like <startvalue<unit>>-<endvalue<unit>>, or <startvalue>-<endvalue>
        # e.g. sch_params: {'CQ2': '130fF', 'npn13G1': 'npn13G2', 'fingers': '10', 'R1': '50Ohm', 'I5': 'Ibase_pp', 'I3': 'Iin_pp', 'I7': 'Icc_pp', 'Icc_pp': '1mA-20mA', 'Iin_pp': '100nA', 'Ibase_pp': '20uA'}
        # e.g. sch_params: {'CQ2': '130fF', 'npn13G1': 'npn13G2', 'fingers': '10', 'R1': '50Ohm', 'I5': 'Ibase_pp', 'I3': 'Iin_pp', 'I7': 'Icc_pp', 'Icc_pp': '1.0e-3-20e-3', 'Iin_pp': '1.0e-9-1.0e-6', 'Ibase_pp': '0.1e-6-10e-6'}
        self.sche_ext = ".sch"

        self.plot_TD_data = True

        self.phase_type = "deg" # "deg" , "rad" Determines the phase data stored in rad or deg in the csv and pandas df

        utils.init_paths(self)

#################
### FUNCTIONS ###
#################
def build_filename(base, ext="", params={}, type=""):
    param_str = "_".join(f"{k}-{v}" for k, v in params.items())
    return f"{base}_{param_str}_{type}{ext}"

def write_params(params, sepIntra="-", sepInter=" "):
    return sepInter.join(f"{k}{sepIntra}{v}" for k, v in params.items())

def read_xyce_csv(path):
    return pd.read_csv(path, delimiter=';', comment='#')

def complex_from_cols(df, real_col, imag_col):
    # Vectorized: returns numpy complex array
    return df[real_col].to_numpy() + 1j * df[imag_col].to_numpy()

def mag_phase(z):
    # z: complex numpy array
    return np.abs(z), np.degrees(np.angle(z))

def at_param(df, col='', val='first'):
    '''
    Returns all rows where the column col has the value val.
    Default for col is the second column.
    Default for val is the very first value of the column col.
    '''
    col_select = col
    if col == '':
        col_select = df.columns[1] # Second column holds the swept parameter
    # print(f"col_select={col_select}")
    
    val_select = val
    if val == 'first':
        val_select = df[col_select].iloc[0]
    elif val == 'last':
        val_select = df[col_select].iloc[-1]

    return df[df[col_select] == val_select]

def power_dBm(I, V, Vph_deg, Iph_deg, type="peak"):
    # Same logic: P = I*V*cos(phiV - phiI), then dBm, then +3
    p_w = I * V * np.cos(np.radians(Vph_deg - Iph_deg))
    p_dBm = 10 * np.log10(p_w * 1000)
    if type == "peak":
        return p_dBm - 3
    elif type == "rms":
        return p_dBm
    elif type == "peak-to-peak":
        pass
    # return 10 * np.log10(p_w * 1000) + 3 # Important to know: We multiply by 2 (add 3 to dBm), because I and V are peak values, not RMS values.

def select_params(params: dict, keys: list[str]) -> dict:
    ''' Return a selection of a dict as a new dict '''
    return {k: params[k] for k in keys if k in params}



############
### MAIN ###
############
def main():
    ui = UI()

    # -------------------------------------------------------------
    # Read schematic file and fill the ui.sch_params
    # -------------------------------------------------------------
    parser.parse_schematic(ui.path_to_file / (ui.filename_base + ui.sche_ext), ui)

    # -------------------------------------------------------------
    # Qucs-S dataset / Xyce dataset conversion
    # -------------------------------------------------------------
    # Path: save_path
    # Filename: <filename_base><naming_params.key1>-<naming_params.value1>_<naming_params.key2>-<naming_params.value2>_<...>.csv

    # First create some defaults.
    naming_params = select_params(ui.sch_params, ui.filename_params)

    filename_path_FD_csv = get_path_filename_FD({
            "path_to_file": ui.path_to_file,
            "filename_base": ui.filename_base,
            "filename_ext": ui.filename_ext_FD,
            "save_path": ui.save_path,
            "params": [f"{k}={v}" for k, v in naming_params.items()]
        })
    filename_path_TD_csv = get_path_filename_TD({
            "path_to_file": ui.path_to_file,
            "filename_base": ui.filename_base,
            "filename_ext": ui.filename_ext_TD,
            "save_path": ui.save_path,
            "params": [f"{k}={v}" for k, v in naming_params.items()]
        })

    if ui.read_orig_data:
        
        print(f"Naming params: {naming_params}")

        filename_path_FD_csv = save_tecplot_FD_as_csv({
            "path_to_file": ui.path_to_file,
            "filename_base": ui.filename_base,
            "filename_ext": ui.filename_ext_FD,
            "save_path": ui.save_path,
            "params": [f"{k}={v}" for k, v in naming_params.items()]
        })

        filename_path_TD_csv = save_tecplot_TD_as_csv({
            "path_to_file": ui.path_to_file,
            "filename_base": ui.filename_base,
            "filename_ext": ui.filename_ext_TD,
            "save_path": ui.save_path,
            "params": [f"{k}={v}" for k, v in naming_params.items()]
        })

    # -------------------------------------------------------------
    # Read converted data as Pandas Dataframe
    # -------------------------------------------------------------
    out_filename_ext = build_filename(ui.filename_base, ext=".csv", params=naming_params, type="FD")

    if ui.save_path != "":
        csv_filename = ui.save_path / out_filename_ext
    df = utils.load_csv(csv_filename)

    # -------------------------------------------------------------
    # Extract swept parameter
    # -------------------------------------------------------------
    # The swept parameter as a string
    swept_params = {}
    for col in df.columns:
        # print(col)
        if (not "FREQ" in col 
        and not col.startswith('Re(') 
        and not col.startswith('Im(') 
        and not col.startswith('V(') 
        and not col.startswith('I(')):
            swept_param = col

            # Determine range and unit of the sept parameter
            swept_param_vals = []
            for val in df[swept_param]:
                if val not in swept_param_vals:
                    swept_param_vals.append(val)

            if swept_param_vals != []:
                swept_params[swept_param] = {'unit': utils.find_unit(swept_param),
                    'range': utils.eng(swept_param_vals[0],0) + '-' + utils.eng(swept_param_vals[-1],0)}
            else:
                swept_params[swept_param] = {'unit': None, 'range': None}
    print(f"The swept parameters: {swept_params}")

    # -------------------------------------------------------------
    # Convert the columns with complex values from strings to actual complex datatype
    # -------------------------------------------------------------
    for col in df.columns:
        if df[col].dtype == "str":  # assume we have a complex value here
            df[col] = df[col].astype(complex)

    if ui.read_orig_data:
        # Add magnitude and phase columns to dataframe
        variables = [col[len("Re("):-1] for col in df.columns if col.startswith("Re(")]
        
        # Compute the complex number and magnitude and phase and add them as columns to the csv
        for var in variables:
            col_real = df[f"Re({var})"]
            col_imag = df[f"Im({var})"]

            # reconstruct complex number
            z = col_real + 1j * col_imag
            
            # Find the right position to insert the complex, magnitude and phase columns
            # (Which is right after the Im column)
            pos = df.columns.get_loc(f"Im({var})") + 1

            # Now insert them
            if var not in df.columns:
                df.insert(pos, var, z)
            df.insert(min(pos+1,len(df.columns)), f"Mag({var})", np.abs(z))
            if ui.phase_type == "rad":
                df.insert(min(pos+2,len(df.columns)), f"Phase({var})", np.angle(z))
            else:
                df.insert(min(pos+2,len(df.columns)), f"Phase({var})", np.degrees(np.angle(z)))
        
        # Replace the csv with the new df
        df.to_csv(csv_filename, sep=",", mode="w", index=False)

    # -------------------------------------------------------------
    # Filter for frequencies
    # -------------------------------------------------------------
    df_dc = utils.at_freq(df, 0)
    df_fundamental = utils.at_freq(df, ui.fundamental)

    # -------------------------------------------------------------
    # Calculate powers
    # -------------------------------------------------------------
    # By using Pandas .values, we extract only the column and get a numpy.ndarray.
    # Without .values we would get a Pandas Series with also the indexes in it.
    # If we have a parameter sweep, the respective values are in the original order.
    # CAUTION! The spectral data that Xyce outputs is two-sided! 
    # That means we have to multiply each spectral component by two.

    power_dc_in = np.real(df_dc["Re(V(VCC))"].values * df_dc["Re(I(VIDC_IN))"].values)

    # The 0.5 comes from the fact that Xyce outputs peak values, but for the power formula we need the RMS of the current and the voltage.
    # Since it is then 1/sqrt(2) * 1/sqrt(2), we have 0.5
    power_rf_in = 0.5 * np.real(2*(df_fundamental["V(VIN)"].values) * 2*np.conj(df_fundamental["I(VIIN)"].values))
    power_rf_out = 0.5 * np.real(2*(df_fundamental["V(VOUT)"].values) * 2*np.conj(df_fundamental["I(VIOUT)"].values))

    power_dc_in_dBm = utils.watt_to_dBm(power_dc_in)
    power_rf_in_dBm = utils.watt_to_dBm(power_rf_in)
    power_rf_out_dBm = utils.watt_to_dBm(power_rf_out)

    # -------------------------------------------------------------
    # Calculate gain
    # -------------------------------------------------------------
    gain = power_rf_out / power_rf_in
    gain_db = power_rf_out_dBm - power_rf_in_dBm

    # -------------------------------------------------------------
    # Calculate efficiencies
    # -------------------------------------------------------------
    dc_to_rf_eff = power_rf_out / power_dc_in
    dc_to_rf_eff_percent = dc_to_rf_eff * 100
    pae = (power_rf_out - power_rf_in) / power_dc_in
    pae_percent = pae * 100

    # -------------------------------------------------------------
    # Save the data for later plotting
    # -------------------------------------------------------------
    df_eval = pd.DataFrame()
    df_eval["FREQ"] = np.full_like(power_dc_in_dBm, ui.fundamental, dtype=float)
    if swept_params:
        for param in swept_params.keys():
            df_eval[param] = df_dc[param].to_numpy()
    df_eval["Power_rf_in_dBm"] = power_rf_in_dBm
    df_eval["Power_dc_in_dBm"] = power_dc_in_dBm
    df_eval["Power_rf_out_dBm"] = power_rf_out_dBm
    df_eval["Dc-to-rf_eff"] = dc_to_rf_eff
    df_eval["Dc-to-rf_eff_percent"] = dc_to_rf_eff_percent
    df_eval["PAE"] = pae
    df_eval["PAE_percent"] = pae_percent
    df_eval["Gain_db"] = gain_db
    
    out_filename = build_filename(ui.filename_base, ext="", params=naming_params)
    df_eval.to_csv(f"{ui.save_path}/eval_{out_filename}.csv", index=False)
    print(f"{ui.save_path}/eval_{out_filename}.csv")
    print(f"{ui.save_path}")

    # Create output directory if necessary
    (ui.save_path / "figs").mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # Plotting
    # -------------------------------------------------------------
    # Important: The Rf input power might not go up monotonic with the input current (experienced if AC current source in series with 50 Ohm resistor as RF source). 
    # So correct for that and use the rf_input_power_sorted whenever the RF input power is the x-axis!
    df_rf_input_power_sorted = df_eval.sort_values(by="Power_rf_in_dBm").reset_index(drop=True)

    # Time domain data plot
    if ui.plot_TD_data:
        plot_TD({
            "path_to_file": filename_path_TD_csv.parent,
            "csv_file": filename_path_TD_csv.name, # str
            "save_path": ui.td_plot_save_path
        })

    if len(swept_params) == 0:
        print(f"DC Input Power: {power_dc_in_dBm[0]} dBm")
        print(f"RF Input Power: {power_rf_in_dBm[0]} dBm")
        print(f"RF Output Power: {power_rf_out_dBm[0]} dBm")
        print(f"DC-to-RF efficiency: {dc_to_rf_eff_percent[0]} %")
        print(f"PAE: {pae_percent[0]} %")
        print(f"Power Gain: {gain_db[0]} dB")

    elif len(swept_params) == 1:

        # RF input power vs input current
        plotter.plot_generic(
            x=df_eval[next(iter(swept_params))].to_numpy(),
            y=df_eval['Power_rf_in_dBm'],
            title="RF input power over input current",
            xlabel="Input current",
            xunit="A",
            ylabel="RF input power",
            yunit="dBm",
            show=False,
            save_path_filename=ui.save_path / "figs" / f"RF_input_power_vs_input_current_{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        )

        # RF input power vs input current sorted
        plotter.plot_generic(
            x=df_rf_input_power_sorted[next(iter(swept_params))].to_numpy(),
            y=df_rf_input_power_sorted['Power_rf_in_dBm'],
            title="RF input power over input current sorted",
            xlabel="Input current",
            xunit="A",
            ylabel="RF input power",
            yunit="dBm",
            show=False,
            save_path_filename=ui.save_path / "figs" / f"RF_input_power_vs_input_current_sorted{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        )

        # # DC input power vs input current
        # plotter.plot_generic(
        #     x=df_eval[next(iter(swept_params))].to_numpy(),
        #     y=df_eval['Power_dc_in_dBm'],
        #     title="DC input power over input current",
        #     xlabel="Input current",
        #     xunit="A",
        #     ylabel="DC input power",
        #     yunit="dBm",
        #     show=False,
        #     save_path_filename=ui.save_path / "figs" / f"DC_input_power_vs_input_current_{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        # )

        # DC input power vs RF input power
        plotter.plot_generic(
            x=df_rf_input_power_sorted['Power_rf_in_dBm'],
            y=df_rf_input_power_sorted['Power_dc_in_dBm'],
            title="DC input power over RF input power",
            xlabel="RF input power",
            xunit="dBm",
            ylabel="DC input power",
            yunit="dBm",
            show=False,
            save_path_filename=ui.save_path / "figs" / f"DC_input_power_vs_RF_input_power_{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        )

        # Output power vs input power
        plotter.plot_generic(
            x=df_rf_input_power_sorted['Power_rf_in_dBm'],
            y=df_rf_input_power_sorted['Power_rf_out_dBm'],
            title="RF output power vs RF input power",
            xlabel="RF input power",
            xunit="dBm",
            ylabel="RF output power",
            yunit="dBm",
            label="@ 60 GHz",
            show=False,
            save_path_filename=ui.save_path / "figs" / f"RF_output_power_vs_RF_input_power_{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        )

        # Gain vs input power
        plotter.plot_compression(
            x=df_rf_input_power_sorted['Power_rf_in_dBm'],
            y=df_rf_input_power_sorted['Gain_db'],
            title="Gain vs RF input power @ 60 GHz",
            xlabel="RF input power",
            xunit="dBm",
            ylabel="Gain",
            yunit="dB",
            show=False,
            save_path_filename=ui.save_path / "figs" / f"Gain_vs_RF_input_power_{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        )

        # PAE vs RF input power
        plotter.plot_generic(
            x=df_rf_input_power_sorted['Power_rf_in_dBm'],
            y=df_rf_input_power_sorted['PAE_percent'],
            title="PAE vs RF input power",
            xlabel="RF input power",
            xunit="dBm",
            ylabel="PAE in %",
            yunit="%",
            label="@ 60 GHz",
            show=False,
            save_path_filename=ui.save_path / "figs" / f"PAE_vs_RF_input_power_{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        )

        # Dc-to-RF efficiency vs RF input power
        plotter.plot_generic(
            x=df_rf_input_power_sorted['Power_rf_in_dBm'],
            y=df_rf_input_power_sorted['Dc-to-rf_eff_percent'],
            title="DC-to-RF efficiency vs RF input power",
            xlabel="RF input power",
            xunit="dBm",
            ylabel="Dc-to-rf efficiency in %",
            yunit="%",
            label="@ 60 GHz",
            show=False,
            save_path_filename=ui.save_path / "figs" / f"DC-to-RF_efficiency_vs_RF_input_power_{write_params(naming_params, sepIntra='-', sepInter='_')}.png"
        )

    elif len(swept_params) == 2:
        # --- DC input power plot ---
        plotter.plot_2p(
        df=df_eval,
        swept_params=swept_params,
        z_col="Power_dc_in_dBm",
        title="DC power in dBm",
        out_name=ui.save_path / "figs" / f"DC_input_power_over_2parameters_{write_params(naming_params, sepIntra="-", sepInter="_")}.png"
        )
        # --- RF input power plot ---
        plotter.plot_2p(
        df=df_eval,
        swept_params=swept_params,
        z_col="Power_rf_in_dBm",
        title="RF input power in dBm",
        out_name=ui.save_path / "figs" / f"RF_input_power_over_2parameters_{write_params(naming_params, sepIntra="-", sepInter="_")}.png"
        )
        # --- RF output power plot ---
        plotter.plot_2p(
        df=df_eval,
        swept_params=swept_params,
        z_col="Power_rf_out_dBm",
        title="RF output power in dBm",
        out_name=ui.save_path / "figs" / f"RF_output_power_over_2parameters_{write_params(naming_params, sepIntra="-", sepInter="_")}.png"
        )

        # --- DC-to-RF efficiency plot ---
        plotter.plot_2p(
        df=df_eval,
        swept_params=swept_params,
        z_col="DC-to-RF_eff_percent",
        title="DC-to-RF efficiency in %",
        out_name=ui.save_path / "figs" / f"DC_to_rf_efficiency_over_2parameters_{write_params(naming_params, sepIntra="-", sepInter="_")}.png"
        )
        # --- PAE efficiency plot ---
        plotter.plot_2p(
        df=df_eval,
        swept_params=swept_params,
        z_col="PAE",
        title="PAE in %",
        out_name=ui.save_path / "figs" / f"PAE_over_2parameters_{write_params(naming_params, sepIntra="-", sepInter="_")}.png"
        )
        # # --- Gain plot ---
        # plotter.plot_2p(
        # df=df_eval,
        # swept_params=swept_params,
        # z_col="Gain_db",
        # title="Gain in dB",
        # out_name=ui.save_path / "figs" / f"Gain_over_2parameters_{write_params(naming_params, sepIntra="-", sepInter="_")}.png"
        # )

    elif len(swept_params) == 3:
        # --- DC input power plot ---
        plotter.plot_3p(
        df=df_eval,
        swept_params=swept_params,
        fixed_param="ICC_PP", # IIN_PP , IBASE_PP , ICC_PP
        z_col="Power_dc_in_dBm",
        title="DC power in dBm"
        )

        # --- RF Input Power plot ---
        plotter.plot_3p(
        df=df_eval,
        swept_params=swept_params,
        fixed_param="ICC_PP", # IIN_PP , IBASE_PP , ICC_PP
        z_col="Power_rf_in_dBm",
        title="RF input power in dBm"
        )

        # --- RF Output Power plot ---
        plotter.plot_3p(
        df=df_eval,
        swept_params=swept_params,
        fixed_param="ICC_PP", # IIN_PP , IBASE_PP , ICC_PP
        z_col="Power_rf_out_dBm",
        title="RF output power in dBm"
        )

        # --- DC-to-RF efficiency plot ---
        plotter.plot_3p(
        df=df_eval,
        swept_params=swept_params,
        fixed_param="ICC_PP", # IIN_PP , IBASE_PP , ICC_PP
        z_col="Dc-to-rf_eff",
        title="DC-to-RF efficiency in %"
        )

        # --- PAE efficiency plot ---
        plotter.plot_3p(
        df=df_eval,
        swept_params=swept_params,
        fixed_param="ICC_PP", # IIN_PP , IBASE_PP , ICC_PP
        z_col="PAE",
        title="PAE in %"
        )

        # # --- Gain plot ---
        # plotter.plot_3p(
        # df=df_eval,
        # swept_params=swept_params,
        # fixed_param="C5", # IIN_PP , IBASE_PP , ICC_PP
        # z_col="Gain_db",
        # title="Gain in db"
        # )

    else:
        print(f"Warning: no plot function implemented for {len(swept_params)} nested parameter sweeps!")


if __name__ == "__main__":
    main()


#########################
### READING TEMPLATES ###
#########################
# Data visualization of a sample pandas data frame after the execution of the above code:
#   | Frequencies  |  Swept params |                                Values
#   |              |               |<----------------------------dtype=float64-------------------------------->|<---------------------------dtype=complex-------------------------->|<------------------------------------dtype=float64------------------------------------->|
'''
          FREQ            C3         Re(I(VIPWR_OUT))     Im(I(VIPWR_OUT))     Re(V(VOUT))       Im(V(VOUT))            I(VIPWR_OUT)                           V(VOUT)                  Mag(I(VIPWR_OUT))       Mag(V(VOUT))       Phase(I(VIPWR_OUT))        Phase(V(VOUT))

0   -96000000000.0       1e-13        3.45985502e-19      -7.84200866e-19     -0.0237141922     -0.0276244963   (-0.000474283844-0.000552489927j)   (-0.0237141922-0.0276244963j)
1   -72000000000.0       1e-13        4.28704478e-19      -3.34814003e-20     0.026147007       -0.0272482005   (0.000522940141-0.00054496401j)     (0.026147007-0.0272482005j)
2   -48000000000.0       1e-13        -8.36648792e-20     2.74032244e-19      0.236044678       -0.0644825765   (0.00472089356-0.00128965153j)      (0.236044678-0.0644825765j)
3   -24000000000.0       1e-13        -8.81243554e-19     0.005025            0.378415218       -0.319385433    (0.00756830437-0.00638770866j)      (0.378415218-0.319385433j)
4              0.0       1e-13        2.93062757e-12      0.0                 1.8614557e-09     0.0             (1.6215752e-11+0j)                  (1.8614557e-09+0j)
5    24000000000.0       1e-13        -8.81243554e-19     -0.005025           0.378415218       0.319385433     (0.00756830437+0.00638770866j)      (0.378415218+0.319385433j)
6    48000000000.0       1e-13        -8.36648792e-20     -2.74032244e-19     0.236044678       0.0644825765    (0.00472089356+0.00128965153j)      (0.236044678+0.0644825765j)
7    72000000000.0       1e-13        4.28704478e-19      3.34814003e-20      0.026147007       0.0272482005    (0.000522940141+0.00054496401j)     (0.026147007+0.0272482005j)
8    96000000000.0       1e-13        3.45985502e-19      7.84200866e-19      -0.0237141922     0.0276244963    (-0.000474283844+0.000552489927j)   (-0.0237141922+0.0276244963j)

9   -96000000000.0    2.68966e-13     5.72376874e-19      -3.22344723e-19     -0.0254494553     -0.0219065225   (-0.000508989107-0.00043813045j)    (-0.0254494553-0.0219065225j)
10  -72000000000.0    2.68966e-13     3.3798861e-19       -9.68100361e-20     0.0148991867      -0.00353275221  (0.000297983734-7.06550442e-05j)    (0.0148991867-0.00353275221j)
11  -48000000000.0    2.68966e-13     -1.08972907e-19     -4.15335992e-20     0.237162205       0.030389107     (0.00474324411+0.000607782141j)     (0.237162205+0.030389107j)
12  -24000000000.0    2.68966e-13     -8.637792e-19       0.005025            0.63474412        -0.11272127     (0.0126948824-0.0022544254j)        (0.63474412-0.11272127j)
13             0.0    2.68966e-13     2.40139864e-12      0.0                 -3.54507051e-09   0.0             (-3.52956059e-11+0j)                (-3.54507051e-09+0j)
14   24000000000.0    2.68966e-13     -8.637792e-19       -0.005025           0.63474412        0.11272127      (0.0126948824+0.0022544254j)        (0.63474412+0.11272127j)
15   48000000000.0    2.68966e-13     -1.08972907e-19     4.15335992e-20      0.237162205       -0.030389107    (0.00474324411-0.000607782141j)     (0.237162205-0.030389107j)
16   72000000000.0    2.68966e-13     3.3798861e-19       9.68100361e-20      0.0148991867      0.00353275221   (0.000297983734+7.06550442e-05j)    (0.0148991867+0.00353275221j)
17   96000000000.0    2.68966e-13     5.72376874e-19      3.22344723e-19      -0.0254494553     0.0219065225    (-0.000508989107+0.00043813045j)    (-0.0254494553+0.0219065225j)
...     ...                  ...             ...                 ...                 
'''
# %%
