# This script contains functions that loads ngspice CSV data into a form compatible with our plotting framework
"""
ngspice_loader.py — Load ngspice wrdata CSVs into the plot_framework API.

ngspice `wrdata` format: for N signals, the CSV has 2N columns:
    t1 v1 t2 v2 ... tN vN
All time columns are identical. This module handles the
interleaved layout and returns data in the (x, y) tuple format
that plot_framework expects.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional


# ── Time unit multipliers ─────────────────────────────────────────
_TIME_SCALES = {"s": 1.0, "ms": 1e3, "us": 1e6, "ns": 1e9, "ps": 1e12}


def load_wrdata(
    csv_path: str | Path,
    labels: list[str],
    time_unit: str = "ns",
    t_range: Optional[tuple[float, float]] = None,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """
    Load an ngspice wrdata CSV and return plot_framework-ready data.

    Parameters
    ----------
    csv_path  : path to the whitespace-separated wrdata CSV
    labels    : signal names, one per wrdata column pair
    time_unit : scale the time axis ("s", "ms", "us", "ns", "ps")
    t_range   : optional (start, end) in *seconds* to window the data

    Returns
    -------
    dict mapping each label to an (x, y) tuple of numpy arrays,
    where x is time in the requested unit and y is voltage.
    Ready to pass directly to iplot, ioverlay, etc.
    """
    csv_path = Path(csv_path)
    raw = pd.read_csv(csv_path, sep=r"\s+", header=None)

    n_signals = len(labels)
    expected_cols = 2 * n_signals
    if raw.shape[1] < expected_cols:
        raise ValueError(
            f"Expected at least {expected_cols} columns for {n_signals} "
            f"signals, got {raw.shape[1]}"
        )

    t = raw.iloc[:, 0].values  # seconds

    # Optional time window (in seconds, before scaling)
    if t_range is not None:
        mask = (t >= t_range[0]) & (t <= t_range[1])
        raw = raw.loc[mask].reset_index(drop=True)
        t = raw.iloc[:, 0].values

    scale = _TIME_SCALES[time_unit]
    t_scaled = t * scale

    traces = {}
    for i, name in enumerate(labels):
        v = raw.iloc[:, 2 * i + 1].values
        traces[name] = (t_scaled, v)

    return traces


def load_sweep(
    file_map: dict[str, tuple[str | Path, list[str]]],
    signal: str,
    time_unit: str = "ns",
    t_range: Optional[tuple[float, float]] = None,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """
    Load multiple wrdata CSVs and extract one signal from each.
    Returns a flat dict suitable for isweep (one slider).

    Parameters
    ----------
    file_map  : {sweep_label: (csv_path, labels_list)}
    signal    : which signal name to extract from each file
    time_unit : time axis unit
    t_range   : optional time window in seconds

    Returns
    -------
    {sweep_label: (t, v)} dict, which can be passed to isweep()
    """
    result = {}
    for sweep_label, (csv_path, labels) in file_map.items():
        traces = load_wrdata(csv_path, labels, time_unit=time_unit, t_range=t_range)
        if signal not in traces:
            raise KeyError(
                f"Signal '{signal}' not in labels {labels} for '{sweep_label}'"
            )
        result[sweep_label] = traces[signal]
        print(traces[signal])
    return result


def load_sweep_overlay(
    sweep_axis: dict[str, dict[str, tuple[str | Path, list[str]]]],
    signal: str,
    time_unit: str = "ns",
    t_range: Optional[tuple[float, float]] = None,
) -> dict[str, dict[str, tuple[np.ndarray, np.ndarray]]]:
    """
    Load a 2D grid of wrdata CSVs: sweep x overlay traces.
    Returns nested dict suitable for isweep_overlay.

    Parameters
    ----------
    sweep_axis : {sweep_label: {trace_label: (csv_path, labels_list)}}
    signal     : which signal to extract from each file
    time_unit  : time axis unit
    t_range    : optional time window in seconds

    Returns
    -------
    {sweep_label: {trace_label: (t, v)}}, which can be passed into isweep_overlay()
    """
    result = {}
    for sweep_label, trace_map in sweep_axis.items():
        inner = {}
        for trace_label, (csv_path, labels) in trace_map.items():
            traces = load_wrdata(csv_path, labels, time_unit=time_unit, t_range=t_range)
            if signal not in traces:
                raise KeyError(
                    f"Signal '{signal}' not in labels {labels} "
                    f"for '{sweep_label}/{trace_label}'"
                )
            inner[trace_label] = traces[signal]
        result[sweep_label] = inner
    return result
