"""Small, deterministic evidence primitives; no Phase 0 writes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def canonical_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value))


def capture(root, directory, name, argv):
    """Record exact argv plus separate, byte-preserved stdout/stderr and exit."""
    root, directory = Path(root), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    record = directory / (name + ".command.json")
    stdout = directory / (name + ".stdout.log")
    stderr = directory / (name + ".stderr.log")
    if any(p.exists() for p in (record, stdout, stderr)):
        raise FileExistsError("refusing to overwrite command evidence")
    started = datetime.now(timezone.utc).isoformat()
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            result = subprocess.run([str(a) for a in argv], cwd=root, stdout=out, stderr=err)
            code = result.returncode
        except OSError as exc:
            err.write(str(exc).encode("utf-8"))
            code = 127
    data = {"argv": [str(a) for a in argv], "cwd": str(root),
            "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
            "returncode": code,
            "stdout": stdout.relative_to(root).as_posix(), "stdout_sha256": sha256(stdout),
            "stderr": stderr.relative_to(root).as_posix(), "stderr_sha256": sha256(stderr)}
    write_new(record, data)
    return data


def seal(directory):
    """Record immutable run payload hashes; the seal itself has no self-hash."""
    directory = Path(directory)
    files = []
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if path.is_file() and "tmp" not in relative.parts and path.name != "seal.json":
            files.append({"path": relative.as_posix(), "sha256": sha256(path),
                          "bytes": path.stat().st_size})
    write_new(directory / "seal.json", {"schema_version": 1, "files": files})
