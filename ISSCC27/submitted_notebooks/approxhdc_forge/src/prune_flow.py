"""Free disk space from finished LibreLane runs.

For every flow/<design>/runs/<tag> whose final/metrics.json exists (the run completed),
delete the per-step working folders (NN-step-name/) and tmp/. Kept: final/ (GDS, netlists,
SPEF, reports, metrics), the run logs/JSON at the run root, config.json, src/ and flow.log.

    python prune_flow.py            # prune once
    python prune_flow.py --watch    # prune every 5 minutes (while a batch is running)
"""
import argparse
import pathlib
import re
import shutil
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
FLOW_DIR = ROOT / "flow"
KEEP_FULL = {"hdc_D512_P32_F64_Q16_exact0_L2_w4_k3_clk20"}   # full sign-off checkpoint run
STEP_DIR = re.compile(r"^\d+-[a-z0-9-]+$")


def prune_once():
    freed = 0
    for run in sorted(FLOW_DIR.glob("hdc_*/runs/*")):
        design = run.parents[1].name
        if design in KEEP_FULL or not (run / "final" / "metrics.json").is_file():
            continue
        targets = [p for p in run.iterdir() if p.is_dir() and (STEP_DIR.match(p.name) or p.name == "tmp")]
        for p in targets:
            assert p.resolve().is_relative_to(FLOW_DIR.resolve()) and p.parent == run
            freed += sum(f.stat().st_size for f in p.rglob("*") if f.is_file() and not f.is_symlink())
            shutil.rmtree(p)
        if targets:
            print(f"pruned {design}/{run.name}: {len(targets)} step folders", flush=True)
    print(f"freed {freed / 2**30:.1f} GB", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    a = ap.parse_args()
    while True:
        prune_once()
        if not a.watch:
            break
        time.sleep(300)
