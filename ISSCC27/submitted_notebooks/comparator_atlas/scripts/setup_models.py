"""Download unmodified model sources; refuse to replace an existing different checkout."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from comparator_atlas.spice import PDK_REVISION

URL = "https://github.com/google/skywater-pdk-libs-sky130_fd_pr.git"


def main() -> None:
    destination = ROOT / ".deps" / "sky130_fd_pr"
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "git", "-c", "core.longpaths=true", "clone", "--quiet", "--depth", "1",
            "--filter=blob:none", "--sparse", "--no-checkout", URL, str(destination),
        ], check=True)
        subprocess.run([
            "git", "-C", str(destination), "fetch", "--quiet", "--depth", "1", "origin", PDK_REVISION,
        ], check=True)
        subprocess.run([
            "git", "-C", str(destination), "sparse-checkout", "set",
            "models", "cells/nfet_01v8", "cells/pfet_01v8", "cells/nfet_01v8_lvt",
        ], check=True)
        subprocess.run([
            "git", "-C", str(destination), "checkout", "--quiet", "--detach", PDK_REVISION,
        ], check=True)
    revision = subprocess.run(
        ["git", "-C", str(destination), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if revision != PDK_REVISION:
        raise RuntimeError(
            f"Existing PDK is at {revision}, not {PDK_REVISION}. It was not modified."
        )
    dirty = subprocess.run(
        ["git", "-C", str(destination), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if dirty:
        raise RuntimeError("Existing PDK contains modifications. It was not modified by setup.")
    if not (destination / "cells" / "nfet_01v8_lvt").is_dir():
        subprocess.run([
            "git", "-C", str(destination), "sparse-checkout", "add", "cells/nfet_01v8_lvt",
        ], check=True)
    print(f"Unmodified SKY130 source verified at {revision}")


if __name__ == "__main__":
    main()
