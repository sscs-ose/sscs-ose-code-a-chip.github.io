"""Notebook display helpers: readable table alignment and a per-section run timer.

Tables: every pandas DataFrame shown in the notebook is rendered as HTML with centred
headers, row labels and long text left-aligned, short text centred and numbers
right-aligned (pandas right-aligns everything by default, which makes sentences hard to
read); a default 0, 1, 2, ... index is not shown.
Timer: records the wall time of every executed code cell, so that the last cell can
report where the run time of a `Run all` went.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import html
import re
import time

import numpy as np
import pandas as pd

SHORT_TEXT = 14          # text columns whose longest entry is at most this many characters are centred

# Readable names for the identifiers that the result files use (run names, column keys, corners).
# Only the rendering changes; the data and every assertion keep the original identifiers.
VALUES = {
    "fpga": "FPGA configuration", "asic": "HSKEM-1 configuration (both choices)",
    "keccak_only": "row-serialized Keccak only", "sram_only": "single-port store only",
    "ntt_opt_ref": "iteration 1: reference (original, single-port)", "ntt_opt_b1": "iteration 1: 1-subtraction Barrett",
    "kyber_ntt_engine (u_shared_ntt)": "NTT engine",
    "keccak_f1600_iter one-round (u_permutation)": "Keccak permutation (one round per clock)",
    "keccak sponge incl. permutation (u_shared_mlkem_sponge)": "Keccak sponge, including the permutation",
    "keygen": "key generation", "encaps": "encapsulation", "ciphertext_final": "ciphertext finalization",
    "decaps": "decapsulation",
    "bank_session_result": "ML-KEM session established", "bank_tx_prepared": "authenticated frame prepared",
    "bank_tamper_result": "altered amount rejected", "bank_withdraw_result": "genuine frame accepted",
    "bank_replay_result": "replayed frame rejected", "bank_zeroize_result": "zeroize executed",
    "bank_post_zeroize_result": "frame after zeroize refused", "bank_demo_result": "complete scenario",
}
HEADERS = {
    "coeffs_checked": "coefficients checked", "cycles_fwd": "cycles, forward NTT", "cycles_inv": "cycles, inverse NTT",
    "timing_variations": "latency variations", "model_fwd_or_perm": "model: forward NTT / permutation",
    "model_inv": "model: inverse NTT", "cycles_measured": "cycles measured", "serial": "row-serialized",
    "variant": "design", "clk_ns": "clock target [ns]", "clk_target_ns": "clock target [ns]",
    "cell_area_um2": "cell area [µm²]", "die_area_um2": "die area [µm²]", "abc_comb_delay_ns": "ABC delay estimate [ns]",
    "flow_rc": "flow exit code", "flops": "flip-flops", "wns_ns": "design WNS [ns]",
    "reg2reg_slack_ns": "reg→reg slack [ns]", "fmax_mhz": "reg→reg fmax [MHz]", "fmax_design_mhz": "design fmax [MHz]",
    "drc_errors": "DRC errors", "antenna_violating_nets": "antenna violations",
    "latency_us_at_fmax": "latency at fmax [µs]", "at_product": "area × time [mm²·µs]",
    "sim_errors": "simulation errors", "est_fwd_latency_us": "estimated forward latency [µs]",
    "area_vs_ref": "area vs reference", "delay_vs_ref": "delay vs reference", "latency_vs_ref": "latency vs reference",
    "gls_pass": "gate-level simulation passed", "decaps_cycles": "decapsulation cycles",
    "decaps_keccak_permutations": "Keccak permutations", "shared_secret_fingerprints": "shared-secret fingerprints",
    "tb_result": "testbench result", "run": "run", "result_pass": "passed", "keygen_cycles": "key generation [cycles]", "encaps_cycles": "encapsulation [cycles]", "ciphertext_final_cycles": "ciphertext finalization [cycles]", "decaps_ms_at_50MHz": "decapsulation at 50 MHz [ms]",
    "delta_vs_fpga": "change vs FPGA configuration", "alms_needed": "ALMs", "block_memory_bits": "block-memory bits",
    "m20k": "M20K blocks", "dsp": "DSP blocks", "saturated": "saturated runs",
    "core_time_ms (at median)": "core time at median [ms]", "runs_per_trace": "runs per trace",
    "max_abs_t": "peak |t|", "cycles_over_4p5": "cycles with |t| > 4.5", "fraction_over_4p5": "share of cycles with |t| > 4.5",
    "control_max_abs_t": "negative control: peak |t|", "control_cycles_over_4p5": "negative control: cycles with |t| > 4.5",
    "PASS": "runs passed",
}
CORNERS = {"ss_100C_1v60": "slow corner (ss, 100 °C, 1.60 V)", "tt_025C_1v80": "typical corner (tt, 25 °C, 1.80 V)",
           "ff_n40C_1v95": "fast corner (ff, −40 °C, 1.95 V)"}


def label(s):
    """Readable name for a run or configuration identifier; anything else is returned unchanged."""
    if not isinstance(s, str):
        return s
    if s in VALUES:
        return VALUES[s]
    if s in CORNERS:
        return CORNERS[s]
    m = re.fullmatch(r"(.+?)_(\d+)ns(_hm\d+)?", s)
    if m and m[1] in VALUES:
        return f"{VALUES[m[1]]}, {m[2]} ns" + (", hold margin" if m[3] else "")
    return s


def header(h) -> str:
    h = "" if h is None else str(h)
    if h in HEADERS:
        return HEADERS[h]
    for code, name in CORNERS.items():
        h = h.replace(code, name)
    return h
_TH = "text-align:center;vertical-align:bottom;padding:4px 10px"
_TD = "padding:3px 10px;vertical-align:top;text-align:"


def _decimals(col: pd.Series) -> int:
    """Common number of decimals for a float column, as pandas would print it (at most four)."""
    d = 0
    for v in col.dropna():
        s = np.format_float_positional(float(v), trim="-")
        d = max(d, len(s.split(".")[1]) if "." in s else 0)
    return min(d, 4)


def _column(col: pd.Series) -> tuple[list[str], str]:
    """Formatted cells and alignment of one column."""
    if pd.api.types.is_bool_dtype(col):
        return [str(v) for v in col], "center"
    if pd.api.types.is_float_dtype(col):
        d = _decimals(col)
        return ["" if pd.isna(v) else f"{v:.{d}f}" for v in col], "right"
    if pd.api.types.is_numeric_dtype(col):
        return [str(v) for v in col], "right"
    cells = ["" if v is None or (isinstance(v, float) and np.isnan(v)) else str(label(v)) for v in col]
    return cells, "center" if max((len(c) for c in cells), default=0) <= SHORT_TEXT else "left"


def table_html(df: pd.DataFrame, index: bool = True) -> str:
    """HTML for a DataFrame with the alignment rules above."""
    index = index and not (isinstance(df.index, pd.RangeIndex) and df.index.name is None)
    frame = df.reset_index() if index else df.reset_index(drop=True)
    if index and frame.columns[0] == "index":
        frame = frame.rename(columns={"index": ""})
    heads = [header(c) for c in frame.columns]
    if index and frame.columns[0] in ("", "index") and df.index.name:
        heads[0] = header(df.index.name)
    cols = [_column(frame.iloc[:, j]) for j in range(frame.shape[1])]
    out = ['<table style="border-collapse:collapse;margin:4px 0">', "<thead><tr>"]
    out += [f'<th style="{_TH}">{html.escape(h)}</th>' for h in heads]
    out.append("</tr></thead><tbody>")
    for i in range(len(frame)):
        out.append("<tr>")
        for j, (cells, align) in enumerate(cols):
            if index and j == 0:          # row labels: left-aligned and bold
                align = "left;font-weight:600"
            out.append(f'<td style="{_TD}{align}">{html.escape(cells[i])}</td>')
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


class _Table:
    def __init__(self, df: pd.DataFrame, index: bool):
        self.df, self.index = df, index

    def _repr_html_(self) -> str:
        return table_html(self.df, self.index)

    def __repr__(self) -> str:
        return self.df.to_string(index=self.index)


def show(df: pd.DataFrame, index: bool = False):
    """Display a table without its index (for tables whose rows are already labelled)."""
    from IPython.display import display
    display(_Table(df, index))


_starts: list[float] = []
DURATIONS: list[float] = []


def install() -> None:
    """Render DataFrames with table_html and start the per-cell timer."""
    from IPython import get_ipython
    ip = get_ipython()
    ip.display_formatter.formatters["text/html"].for_type(pd.DataFrame, table_html)

    def pre(*_):
        _starts.append(time.time())

    def post(*_):
        if _starts:
            DURATIONS.append(time.time() - _starts.pop())

    ip.events.register("pre_run_cell", pre)
    ip.events.register("post_run_cell", post)
