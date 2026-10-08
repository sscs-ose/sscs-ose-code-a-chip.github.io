"""Exercise the real public-source bootstrap and its restart path in an isolated folder."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entry_tools import verify_files

NOTEBOOK = "Comparator_Atlas.ipynb"
PARTS = ("ISSCC27", "submitted_notebooks", "comparator_atlas")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True,
                        help="Where to save the completed bootstrap verification receipt")
    args = parser.parse_args()
    source = ROOT / NOTEBOOK
    release_map = ROOT / "entry_checksums.json"
    if not source.is_file() or not release_map.is_file():
        raise RuntimeError("Run this check from the complete packaged/public entry, not an unsealed workspace")
    verify_files(ROOT, json.loads(release_map.read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory(prefix="atlas-review-") as directory:
        isolated = Path(directory)
        shutil.copyfile(source, isolated / NOTEBOOK)
        for attempt in (1, 2):
            subprocess.run(
                [sys.executable, "-m", "pytest", "--nbmake", "--nbmake-timeout=600", NOTEBOOK, "-q"],
                cwd=isolated, check=True,
            )
            downloaded = isolated / "comparator-atlas-source"
            downloaded_entry = downloaded.joinpath(*PARTS)
            downloaded_map = downloaded_entry / "entry_checksums.json"
            if not downloaded_map.is_file() or downloaded_map.read_bytes() != release_map.read_bytes():
                raise RuntimeError("The public bootstrap fetched a different release from the candidate under review")
            if (downloaded_entry / NOTEBOOK).read_bytes() != source.read_bytes():
                raise RuntimeError("The public notebook source differs from the candidate under review")
            verify_files(downloaded_entry, json.loads(downloaded_map.read_text(encoding="utf-8")))
            revision = subprocess.check_output(
                ["git", "-C", str(downloaded), "rev-parse", "HEAD"], text=True,
            ).strip()
            print(f"Public-source bootstrap pass {attempt}/2: {revision}", flush=True)
        receipt = {
            "status": "passed",
            "scenario": "Notebook-only cold start followed by a second run reusing the complete downloaded source.",
            "actual_public_source_commit": revision,
            "notebook_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "entry_checksums_sha256": hashlib.sha256(release_map.read_bytes()).hexdigest(),
            "notebook_executions": 2,
            "public_release_bytes_match_candidate": True,
            "new_spice_executions": 0,
            "real_google_colab_runtime_executed": False,
            "qualification": "Linux/Python notebook bootstrap and restart verification, not a Google-account session.",
        }
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Saved bootstrap receipt: {args.artifact}")


if __name__ == "__main__":
    main()
