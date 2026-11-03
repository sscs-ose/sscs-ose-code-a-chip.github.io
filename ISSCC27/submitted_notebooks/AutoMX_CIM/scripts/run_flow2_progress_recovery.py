#!/usr/bin/env python3
"""Resume six validated core jobs; repair routed ARC and probe full ADC RC."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_dc_antenna_recovery as campaign


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--source-tag", default="startup_guard_20261018_03")
    p.add_argument("--tag", default="readout_progress_20261018_04")
    p.add_argument("--pdk-root", type=Path, default=campaign.closure.acquisition.DEFAULT_PDK)
    p.add_argument("--openlane-source", type=Path, default=campaign.fanout.notebook.DEFAULT_SOURCE)
    p.add_argument("--openlane-pdk", type=Path, default=campaign.fanout.notebook.DEFAULT_PDK)
    p.add_argument("--run", action="store_true")
    p.add_argument("--skip-fanout", action="store_true")
    p.add_argument("--timeout-s", type=int, default=1800)
    p.add_argument("--openlane-timeout-s", type=int, default=7200)
    a = p.parse_args()
    result = campaign.run(a.root, source_tag=a.source_tag, tag=a.tag,
        pdk_root=a.pdk_root, openlane_source=a.openlane_source, openlane_pdk=a.openlane_pdk,
        execute=a.run, timeout_s=a.timeout_s, openlane_timeout_s=a.openlane_timeout_s,
        include_fanout=not a.skip_fanout, startup_guards=True, progress_profile=True)
    print(json.dumps(result, indent=2))
    if a.run and result["status"] != "MEASURED_DC_ANTENNA_PROTOTYPES_NOT_WRAPPER_SIGNOFF":
        raise SystemExit(1)
