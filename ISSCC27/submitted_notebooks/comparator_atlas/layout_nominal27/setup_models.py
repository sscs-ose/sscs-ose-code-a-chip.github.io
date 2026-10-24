"""Fetch only the exact three-flavor model source into this job's private work area."""

from pathlib import Path
import shutil
import subprocess
import sys

from contract import PROTOCOL, require, sha256, write_json


def main() -> None:
    destination, evidence = map(lambda arg: Path(arg).resolve(), sys.argv[1:3])
    require(not destination.exists(), "Refusing to overwrite/reuse model checkout")
    pin = PROTOCOL["tools"]["models"]
    destination.mkdir(parents=True)
    commands = [
        ["init", "--quiet"],
        ["config", "core.autocrlf", "false"],
        ["remote", "add", "origin", f'https://github.com/{pin["repository"]}.git'],
        ["config", "remote.origin.promisor", "true"],
        ["config", "remote.origin.partialclonefilter", "blob:none"],
        ["fetch", "--quiet", "--depth=1", "--filter=blob:none", "origin", pin["commit"]],
        ["sparse-checkout", "set", "--cone", "models", "cells/nfet_01v8",
         "cells/nfet_01v8_lvt", "cells/pfet_01v8"],
        ["checkout", "--quiet", "--detach", "FETCH_HEAD"],
    ]
    evidence.mkdir(parents=True, exist_ok=True)
    with (evidence / "model-checkout.log").open("w") as log:
        for arguments in commands:
            command = ["git", "-C", str(destination), *arguments]
            log.write("COMMAND: " + " ".join(command) + "\n")
            log.flush()
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT,
                           timeout=120)
    revision = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
    require(revision == pin["commit"], "Incorrect actual model revision")
    dirty = subprocess.check_output(
        ["git", "-C", str(destination), "status", "--porcelain", "--untracked-files=no"],
        text=True).strip()
    require(not dirty, "Modified model source")
    license_path = destination / "LICENSE"
    require(license_path.is_file(), "Missing original model-source license")
    shutil.copyfile(license_path, evidence / "model-source-license.txt")
    paths = [p for root in (destination / "models", destination / "cells")
             for p in root.rglob("*") if p.is_file()]
    for flavor in ("nfet_01v8", "nfet_01v8_lvt", "pfet_01v8"):
        require((destination / "cells" / flavor
                 / f"sky130_fd_pr__{flavor}__tt.pm3.spice").is_file(),
                f"Missing actual {flavor} model")
    write_json(evidence / "models.json", {
        "repository": pin["repository"], "revision": revision,
        "tracked_files_modified": False, "source_file_count": len(paths),
        "license_sha256": sha256(license_path),
        "source_bytes": sum(p.stat().st_size for p in paths),
        "files": {str(p.relative_to(destination)).replace("\\", "/"): sha256(p)
                  for p in sorted(paths)},
    })
    print(f"Exact unmodified model checkout: {revision}, {len(paths)} files")


if __name__ == "__main__":
    main()
