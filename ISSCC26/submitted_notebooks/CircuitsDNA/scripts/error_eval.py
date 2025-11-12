#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

def compute_error_metrics(filename, max_true_abs=None):

    # Read in files
    df = pd.read_csv(filename, sep=r'\s+', engine='python')

    if max_true_abs is None:
        max_true_abs = df['Expected'].abs().max()

    diff = (df['Expected'] - df['OUT']).astype(np.int64)
    abs_diff = diff.abs()
    gt_abs = df['Expected'].abs()
    ap_abs = df['OUT'].abs()

    B = len(df)

    sum_abs = abs_diff.sum()
    err_cnt = (abs_diff != 0).sum()
    worst = abs_diff.max()

    # MRE
    mask_nonzero = gt_abs != 0
    sum_rel_ex0 = (abs_diff[mask_nonzero] / gt_abs[mask_nonzero]).sum()
    cnt_rel = mask_nonzero.sum()
    MRE = (sum_rel_ex0 / cnt_rel) if cnt_rel > 0 else 0.0

    # sMAPE
    denom = 0.5 * (gt_abs + ap_abs) + 1e-9
    sMAPE = (abs_diff / denom).mean()

    # NMED / ER / WCE
    NMED = sum_abs / (B * max_true_abs)
    ER = err_cnt / B
    WCE = worst / max_true_abs

    print(f"Samples (B): {B}")
    print(f"MAX_TRUE_ABS: {max_true_abs}")
    print(f"NMED  = {NMED:.6e}")
    print(f"ER    = {ER:.6e}")
    print(f"WCE   = {WCE:.6e}")
    print(f"MRE   = {MRE:.6e}")
    print(f"sMAPE = {sMAPE:.6e}")

    return dict(NMED=NMED, ER=ER, WCE=WCE, MRE=MRE, sMAPE=sMAPE)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Compute error metrics from extracted_truth_table.txt")
    p.add_argument("file", help="Path to extracted_truth_table.txt")
    p.add_argument("--maxabs", type=float, default=None, help="Override MAX_TRUE_ABS (default: use max |Expected|)")
    args = p.parse_args()
    compute_error_metrics(args.file, args.maxabs)
