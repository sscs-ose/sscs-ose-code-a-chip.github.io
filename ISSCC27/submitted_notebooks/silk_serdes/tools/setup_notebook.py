"""Install the notebook environment; safe to rerun with matching tools/models.

The main notebook runs this script before importing its circuit modules.
Silk is installed from PyPI; the notebook downloads this project when opened in Colab.
"""

from pathlib import Path
import os, sys, json, subprocess, shutil, hashlib
from importlib import metadata

os.environ.setdefault("MPLBACKEND", "Agg")

try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

PROJECT = Path.cwd().resolve()
if not (PROJECT / "circuits/transmitter.py").is_file():
    raise RuntimeError("Open the notebook from the complete project folder, or run its Colab download cell first.")
(PROJECT / "artifacts").mkdir(exist_ok=True)
print("Project:", PROJECT)


# Install the published release, replacing an older local candidate if present.
pins = json.loads((PROJECT / "environment.json").read_text())
requirement = "circuitsilk==" + pins["silk"]["version"]
try:
    installed = metadata.distribution("circuitsilk")
    installed_version = installed.version
    installed_direct_url = json.loads(installed.read_text("direct_url.json") or "{}")
except metadata.PackageNotFoundError:
    installed_version, installed_direct_url = None, {}
if installed_version != pins["silk"]["version"] or installed_direct_url:
    if "silk" in sys.modules:
        raise RuntimeError("Restart the kernel, then run setup before importing Silk.")
    pip = [sys.executable, "-m", "pip", "install", "--index-url", pins["silk"]["index_url"]]
    if installed_direct_url:
        # A candidate may have the same version number as the public release.
        subprocess.run(pip + ["--force-reinstall", "--no-deps", requirement], check=True)
    subprocess.run(pip + [requirement], check=True)
print("Silk:", metadata.version("circuitsilk"))

from silk import ModuleTestbench
if not all(hasattr(ModuleTestbench, name) for name in ("set_variable_values", "set_groups")):
    raise RuntimeError("This Silk build is too old for the demo. Install circuitsilk==0.2.0 from PyPI and restart the kernel.")


# Colab permits package installation; an existing local ngspice is reused.
if IN_COLAB:
    os.environ["SILK_SETTINGS"] = "/dev/null"
    subprocess.run(["apt-get", "update", "-qq"], check=True)
    subprocess.run(["apt-get", "install", "-y", "ngspice"], check=True)
    os.environ["SILK_NGSPICE_BIN"] = shutil.which("ngspice")

# Silk API: resolve simulator and PDK settings for this environment.
from silk.settings import lookup
ngspice = shutil.which(lookup("SILK_NGSPICE_BIN").value)
if ngspice is None:
    raise RuntimeError("ngspice is missing. Use a Colab runtime for automatic system-package installation.")
print(subprocess.check_output([ngspice, "--version"], text=True))


# Reuse installed models, or download the pinned open_pdks builds with pdksetup.
PDK_ROOT = (PROJECT / ".pdk") if IN_COLAB else Path(lookup("PDK_ROOT").value).expanduser()
os.environ["PDK_ROOT"] = str(PDK_ROOT)
PDKSETUP_COMMIT = "703e8eb5d89710026976ec49fd1b9e0785a3f705"
missing = []
for family, variant in (("sky130", "sky130A"), ("gf180mcu", "gf180mcuD")):
    pin = pins["pdks"][variant]
    sources = PDK_ROOT / variant / "SOURCES"
    correct_revision = sources.is_file() and f"open_pdks {pin['open_pdks']}" in sources.read_text().splitlines()
    if not correct_revision or not (PDK_ROOT / variant / pin["library"]).is_file():
        missing.append((family, variant))
if missing:
    subprocess.run([sys.executable, "-m", "pip", "install",
                    f"https://github.com/levantlabs/pdksetup/archive/{PDKSETUP_COMMIT}.zip",
                    "volare==0.20.6"], check=True)
    # pdksetup launches volare by name. Include this kernel's installed scripts
    # even when Jupyter was started without activating the virtual environment.
    import sysconfig
    scripts = sysconfig.get_path("scripts")
    pdk_env = dict(os.environ, PATH=scripts + os.pathsep + os.environ.get("PATH", ""))
    pdk_cli = str(Path(scripts) / "pdk")
    # Volare's CLI uses a five-second network timeout. Its Python API lets
    # large model downloads tolerate stalls without patching the package.
    import time
    import httpx
    from volare import fetch
    from volare.github import GitHubSession
    for family, variant in missing:
        with GitHubSession(timeout=120.0) as download_session:
            for attempt in range(1, 4):
                try:
                    fetch(str(PDK_ROOT), family, pins["pdks"][variant]["open_pdks"],
                          session=download_session)
                    break
                except (httpx.TimeoutException, httpx.NetworkError) as error:
                    if attempt == 3:
                        raise RuntimeError(f"{family} download failed after 3 attempts; rerun setup to retry.") from error
                    print(f"{family}: network interruption ({error}); retrying download ({attempt}/3).", flush=True)
                    time.sleep(5)
        # pdksetup activates the downloaded revision and records its installation.
        subprocess.run([pdk_cli, "install", family, "--version", pins["pdks"][variant]["open_pdks"],
                        "--pdk-root", str(PDK_ROOT), "--config", str(PROJECT / "artifacts/pdksetup.toml")], check=True, env=pdk_env)
for variant, pin in pins["pdks"].items():
    if not (PDK_ROOT / variant / pin["library"]).is_file():
        raise RuntimeError(f"Missing model library for {variant}.")
    if f"open_pdks {pin['open_pdks']}" not in (PDK_ROOT / variant / "SOURCES").read_text().splitlines():
        raise RuntimeError(f"Wrong model revision for {variant}.")
# Silk CLI: check the installed tools, models, and Python dependencies.
subprocess.run([sys.executable, "-m", "silk.doctor"], check=True)

# Save the software, model paths and source versions used for this run.
# This record helps another designer reproduce the results later.
from dataclasses import asdict
from datetime import datetime, timezone
import silk

DEMO_ROOT = PROJECT
ARTIFACTS = DEMO_ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

installation = metadata.distribution("circuitsilk")
direct_url = json.loads(installation.read_text("direct_url.json") or "{}")
wheel_hash = direct_url.get("archive_info", {}).get("hashes", {}).get("sha256")
source_commit = None
if direct_url.get("dir_info", {}).get("editable"):
    result = subprocess.run(["git", "-C", str(Path(silk.__file__).parent), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    if result.returncode == 0:
        source_commit = result.stdout.strip()

local_sources = sorted([*DEMO_ROOT.glob("circuits/*.py"),
                        *DEMO_ROOT.glob("characterization/*.py"),
                        *DEMO_ROOT.glob("requirements*"),
                        DEMO_ROOT / "environment.json", DEMO_ROOT / "tools/setup_notebook.py"])
provenance = {
    "local_source_sha256": {str(path.relative_to(DEMO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in local_sources},
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.version.split()[0],
    "interpreter": sys.executable,
    "silk_import": str(Path(silk.__file__).resolve()),
    "silk_source_commit": source_commit,
    "silk_wheel_sha256": wheel_hash,  # Observed only for direct archive installs.
    "silk_published_wheel_sha256": pins["silk"]["published_wheel_sha256"],
    "silk_install_direct_url": direct_url,
    "circuit_source": json.loads((DEMO_ROOT / "source_provenance.json").read_text()),
    "packages": {name: metadata.version(name) for name in ("circuitsilk", "numpy", "matplotlib")},
    "ngspice": ngspice,
    "silk_settings": {name: asdict(lookup(name)) for name in
                      ("SILK_NGSPICE_BIN", "SILK_XYCE_BIN", "PDK_ROOT")},
    "pdk_root_setting": str(PDK_ROOT),
    "pdk_revisions": {variant: (PDK_ROOT / variant / "SOURCES").read_text().strip()
                      for variant in pins["pdks"]},
}
(ARTIFACTS / "environment.json").write_text(json.dumps(provenance, indent=2) + "\n")
print("Environment details saved in artifacts/environment.json")

# Keep each notebook execution's results in a separate folder.
# UUID supplies a unique folder name; it has no effect on the circuit.
from uuid import uuid4
REVIEW = ARTIFACTS / ("review_" + uuid4().hex[:8])
REVIEW.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = str(REVIEW / "design_history.sqlite")
print("Results folder:", REVIEW)
