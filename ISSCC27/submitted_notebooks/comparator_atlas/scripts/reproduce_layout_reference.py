"""Prepare the exact public historical source for an optional disposable-Linux replay."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entry_tools import digest, verify_files

REPOSITORY = "https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io.git"
REVISION = "68832ec0ae7c526afcb4cded405a0bfd753a65c3"
CHECKSUM_FILE_SHA256 = "3fdab3b8fbe040550393153b44c0931548088aaa43ceb71fc56304c0cbe5d720"
PARTS = ("ISSCC27", "submitted_notebooks", "comparator_atlas")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", required=True,
                        help="Download and verify source only; never install tools or execute experiments")
    parser.parse_args()
    destination = ROOT / ".cache" / "layout_reference_68832ec0"
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "git", "-c", "core.autocrlf=false", "clone", "--quiet", "--no-checkout",
            "--depth", "1", "--filter=blob:none", REPOSITORY, str(destination),
        ], check=True)
        subprocess.run(["git", "-C", str(destination), "config", "core.autocrlf", "false"], check=True)
        subprocess.run(["git", "-C", str(destination), "sparse-checkout", "set", "/".join(PARTS)], check=True)
        subprocess.run(["git", "-C", str(destination), "fetch", "--quiet", "--depth", "1", "origin", REVISION],
                       check=True)
        subprocess.run(["git", "-C", str(destination), "checkout", "--quiet", "--detach", REVISION], check=True)
    revision = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True,
    ).strip()
    changed = subprocess.check_output(
        ["git", "-C", str(destination), "status", "--porcelain", "--untracked-files=no"], text=True,
    ).strip()
    if revision != REVISION or changed:
        raise RuntimeError("Existing reference source differs; it was not reset or overwritten")
    entry = destination.joinpath(*PARTS)
    checksums = entry / "entry_checksums.json"
    if digest(checksums) != CHECKSUM_FILE_SHA256:
        raise RuntimeError("The historical entry checksum identity does not match the recorded experiment")
    verify_files(entry, json.loads(checksums.read_text(encoding="utf-8")))
    print(f"Exact source prepared and verified at {REVISION}")
    print(f"Entry directory: {entry}")
    print("No system package, Magic, Netgen, or SPICE process was installed or executed.")
    print("For an optional full replay, use a disposable Ubuntu 24.04 environment and its pinned ci.yml.")
    print("From the prepared entry: bash layout_compact_repair/run.sh")
    print("The original 1 ns pilot is expected to fail; retain that outcome and its evidence.")


if __name__ == "__main__":
    main()
