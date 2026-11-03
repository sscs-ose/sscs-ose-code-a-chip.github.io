"""Command-line entry points for the receipt-backed SKY130 flow."""
from __future__ import annotations

import argparse
from pathlib import Path

from .attention import run_stage1, write_stage1_receipt
from .circuit import discover_sky130_model_library, generate_stage4_spice
from .config import Sky130MHAConfig
from .environment import capture_environment, write_environment_receipt
from .scheduler import write_stage2_schedule
from .spice import run_stage4_manifest

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m automx_cim")
    subparsers = parser.add_subparsers(dest="stage", required=True)
    for stage, description in (("stage0", "capture SKY130 environment/configuration receipt"),
                               ("stage1", "run deterministic tiny-MHA numerical reference"),
                               ("stage2", "write dependency-aware tiny-MHA tile schedule")):
        sub = subparsers.add_parser(stage, help=description)
        sub.add_argument("--config", type=Path, default=Path("configs/sky130_mha_tiny.json"))
        sub.add_argument("--output-dir", type=Path, default=Path("results/receipts"))
    stage4 = subparsers.add_parser("stage4", help="generate and validate SKY130 cell/columns/4x4 macro")
    stage4.add_argument("--config", type=Path, default=Path("configs/sky130_mha_tiny.json"))
    stage4.add_argument("--output-dir", type=Path, default=Path("generated/sky130/spice"))
    stage4.add_argument("--receipt-dir", type=Path, default=Path("results/receipts/spice"))
    stage4.add_argument("--model-library", type=Path)
    stage4.add_argument("--pdk-root", type=Path)
    stage4.add_argument("--level", action="append", choices=["cell", "column4", "column8", "macro4x4", "all"])
    stage4.add_argument("--generate-only", action="store_true")
    stage4.add_argument("--timeout", type=int, default=900)
    return parser

def main() -> None:
    args = _parser().parse_args(); config = Sky130MHAConfig.from_json(args.config)
    if args.stage == "stage0":
        receipt = capture_environment(config, root=Path.cwd()); path = args.output_dir / "environment.json"
        write_environment_receipt(receipt, path); print(f"Wrote {path}")
    elif args.stage == "stage1":
        receipt = write_stage1_receipt(run_stage1(config), args.output_dir)
        print(f"Wrote {args.output_dir / 'stage1_mha_tiny.json'}"); print("metrics:", receipt["metrics"])
    elif args.stage == "stage2":
        manifest = write_stage2_schedule(config, args.output_dir)
        print(f"Wrote {args.output_dir / 'mha_tiny_schedule.json'}"); print("breakdown:", manifest["breakdown"])
    else:
        model = args.model_library.resolve() if args.model_library else discover_sky130_model_library(args.pdk_root)
        manifest = generate_stage4_spice(config, args.output_dir, model, tuple(args.level or ["all"]), args.receipt_dir)
        manifest_path = args.output_dir / "stage4_manifest.json"
        print(f"Generated {len(manifest['artifacts'])} level(s): {manifest_path}")
        if not args.generate_only:
            receipts = run_stage4_manifest(manifest_path, timeout_s=args.timeout)
            print("Validated:", ", ".join(receipt["stage"] for receipt in receipts))

if __name__ == "__main__": main()