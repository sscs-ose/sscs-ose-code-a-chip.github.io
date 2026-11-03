"""Application run folders and explicit native dependency checks."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

HERE = Path(__file__).resolve().parent


def new_run(label="notebook"):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = HERE / "local_runs" / f"{label}_{stamp}_{uuid4().hex[:8]}"
    path.mkdir(parents=True)
    return path


def check_device_runtime():
    """Run native imports in a child: missing libraries can abort the interpreter."""
    script = "import numpy, scipy, pyvista, gmsh, devsim; gmsh.initialize(); gmsh.finalize()"
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(
            "Device runtime unavailable. On Debian/Ubuntu install libblas3, liblapack3, "
            "libopenblas0-pthread and libglu1-mesa, then the notebook requirements. "
            "See SETUP.md. Native diagnostic:\n" + result.stdout + result.stderr
        )
    return result.stdout.strip()
