from pathlib import Path
import numpy as np
import pandas as pd
import math

def load_csv(file: Path):
    return pd.read_csv(file, sep=",")

def at_freq(df, freq):
    '''
    Returns all rows where FREQ has a value equal to freq.
    Use .copy() to make it saver if the returned df is 
    modified later.
    '''
    return df.loc[df["FREQ"].eq(freq)].copy()

def at_freqs(df, freqs):
    '''
    Returns all rows where FREQ has a value listed in freqs.
    Use .copy() to make it saver if the returned df is 
    modified later.
    '''
    return df.loc[df["FREQ"].isin(freqs)].copy()

def at_param(df, col='', val='first'):
    '''
    Returns all rows where the column col has the value val.
    Default for col is the second column.
    Default for val is the very first value of the column col.
    '''
    col_select = col
    if col == '':
        col_select = df.columns[1] # Second column holds the swept parameter
    
    val_select = val
    if val == 'first':
        val_select = df[col_select].iloc[0]
    elif val == 'last':
        val_select = df[col_select].iloc[-1]

    return df[df[col_select] == val_select]

def is_param(val: str) -> bool:
    if (not val.startswith("V(") and not val.startswith("I(V") and not 
        val.startswith("FREQ") and not val.startswith("TIME")):
        return True
    else:
        return False
    


def find_unit(param: str) -> str:
    if param.startswith("V(") or param.startswith("I(V"):
        param = clean_item(param)

    if param == "":
        return ""
    elif param.startswith("V"):
        return "V"
    elif param.startswith("I"):
        return "A"
    elif param.startswith("R"):
        return "Ω"
    elif param.startswith("L"):
        return "H"
    elif param.startswith("C"):
        return "F"
    elif param.startswith("P"):
        return "W"
    elif param.startswith("G"):
        return "dB"
    elif param.upper().startswith("FUNDAMENTAL") or param.startswith("FREQ"):
        return "Hz"
    elif param.upper().startswith("TIME"):
        return "s"
    
def clean_list(items):
    cleaned = []

    for item in items:
        if item.startswith("V(") and item.endswith(")"):
            item = item[2:-1]  # remove V( and )
        elif item.startswith("I(V") and item.endswith(")"):
            item = item[3:-1]  # remove I(V and )

        cleaned.append(item)

    return cleaned

def clean_item(item):
    if item.startswith("V(") and item.endswith(")"):
        return item[2:-1]  # remove V( and )
    elif item.startswith("I(V") and item.endswith(")"):
        return item[3:-1]  # remove I(V and )
    
def transfer_args_to_ui(args, ui):
    """
    TODO Descrtiption

    Parameters:
        args: dict
    """
    for name, value in args.items():
        if hasattr(ui, name):
            if "path" in name.lower() and value is not None:
                value = Path(value)
            elif isinstance(value, list):
                value = dict(p.split("=") for p in value)

            setattr(ui, name, value)

def init_paths(obj):
    """
    Convert all attributes containing 'path' in their name
    into absolute pathlib.Path objects.
    """
    for attr_name, attr_value in obj.__dict__.items():
        if "path" in attr_name.lower() and isinstance(attr_value, (str, Path)):
            setattr(obj, attr_name, Path(attr_value).expanduser().resolve())

# -------------------------------
# Math operations
# -------------------------------
def watt_to_dBm(p_watt: float | np.ndarray) -> float | np.ndarray:
    """
    Convert power in watts to dBm.

    Parameters
    ----------
    p_watt : float or np.ndarray
        Power value(s) in watts.

    Returns
    -------
    float or np.ndarray
        Power value(s) in dBm. Non-positive input values are mapped to -inf.
    """
    return np.where(
        p_watt > 0,
        10 * np.log10(p_watt / 1e-3),
        -np.inf
    )

def eng(value, precision=3):
    '''Print number in engineering notation'''
    if value == 0:
        return f"{0:.{precision}f}e0"

    exponent = int(math.floor(math.log10(abs(value)) / 3) * 3)
    mantissa = value / (10 ** exponent)

    return f"{mantissa:.{precision}f}e{exponent}"
