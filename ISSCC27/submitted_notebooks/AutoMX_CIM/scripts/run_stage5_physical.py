#!/usr/bin/env python3
"""Run the receipt-gated AutoMX-CIM SKY130 physical-core flow."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from automx_cim.physical import run_stage5, write_preflight_receipt

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default=str(ROOT/'configs/sky130_mha_tiny.json'))
    ap.add_argument('--contract',default=str(ROOT/'physical/sky130/macro/macro_contract.json'))
    ap.add_argument('--pdk-root')
    ap.add_argument('--macro',default='automx_ternary_cim_4x4_core')
    ap.add_argument('--timeout-s',type=int,default=900)
    mode=ap.add_mutually_exclusive_group(); mode.add_argument('--preflight',action='store_true'); mode.add_argument('--all',action='store_true')
    args=ap.parse_args()
    if args.all:
        result=run_stage5(ROOT,args.contract,args.pdk_root,args.timeout_s)
    else:
        result=write_preflight_receipt(ROOT,args.contract,args.pdk_root)
    if result.get('macro') != args.macro: raise SystemExit(f"macro mismatch: {result.get('macro')} != {args.macro}")
    print(json.dumps(result,indent=2))
    if result.get('status')!='PASS': raise SystemExit(1)
if __name__=='__main__': main()