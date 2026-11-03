#!/usr/bin/env python3
"""Generate and optionally validate all Stage-4 SKY130 SPICE levels."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from automx_cim import Sky130MHAConfig
from automx_cim.circuit import discover_sky130_model_library, generate_stage4_spice
from automx_cim.spice import run_stage4_manifest

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "sky130_mha_tiny.json")
    parser.add_argument("--output", type=Path, default=ROOT / "generated" / "sky130" / "spice")
    parser.add_argument("--receipt-dir", type=Path, default=ROOT / "results" / "receipts" / "spice")
    parser.add_argument("--model-library", type=Path)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--level", action="append", choices=["cell", "column4", "column8", "macro4x4", "all"], default=None)
    parser.add_argument("--run", action="store_true", help="run ngspice and write PASS receipts")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    cfg = Sky130MHAConfig.from_json(args.config)
    model = args.model_library.resolve() if args.model_library else discover_sky130_model_library(args.pdk_root)
    levels = tuple(args.level or ["all"])
    manifest = generate_stage4_spice(cfg, args.output, model, levels, args.receipt_dir)
    manifest_path = args.output / "stage4_manifest.json"
    print(f"Generated {len(manifest['artifacts'])} level(s); manifest: {manifest_path}")
    for artifact in manifest["artifacts"]:
        print(f"  {artifact['stage']:9s} {artifact['netlist']}")
    if args.run:
        receipts = run_stage4_manifest(manifest_path, timeout_s=args.timeout)
        for receipt in receipts:
            print(f"PASS {receipt['stage']:9s} energy={receipt['metrics']['dynamic_energy_j']:.6g} J "
                  f"min_sense={receipt['metrics']['minimum_nonzero_sense_v']:.6g} V")
    else:
        print("Generation only. Add --run to execute ngspice and create validated receipts.")
    return 0

if __name__ == "__main__": raise SystemExit(main())