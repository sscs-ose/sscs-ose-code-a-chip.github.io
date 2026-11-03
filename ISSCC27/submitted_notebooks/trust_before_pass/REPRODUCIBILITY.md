> **v0.5:** start at START_HERE.html. Current novice pages need no Python; file opening
> still needs actual reader confirmation. Rebuild with `python build_controls.py`;
> run `python validate_notebook.py` for current notebook/tests. CLEAN_REPRODUCTION_V05.json
> and BROWSER_VALIDATION_V05.json describe actual checks. Earlier notes below are historical.

> **v0.4:** novice readers can open INVESTIGATION_DESK.html directly, with no Python or server.
> STATIC_WORKBOOK.html requires no scripts. For engineering reproduction, the existing Python
> lock is unchanged. Run `python build_controls.py` to regenerate the 51 cached choices,
> `python -m unittest discover -v -s . -p "test_*.py"` to compare them to the checker, then
> `python validate_notebook.py` for the narrative. Current validation is recorded in
> CLEAN_REPRODUCTION_V04.json and BROWSER_VALIDATION_V04.json. The older notes below are historical.

> **v0.3 update:** `CLEAN_REPRODUCTION_V03.json` records the new clean-environment check.
> The older clean-environment and full CACE records below describe v0.2. They do not
> substitute for v0.3 notebook validation or an independent reader trial. The new
> interactive tasks use editable Python parameters, require no widget package, and
> leave answers blank during unattended execution. Core package requirements are unchanged.

# Reproduce Trust Before Pass

The default notebook is an offline lesson with genuine saved evidence. Fresh simulation is an
explicit optional route. Tested host: Windows x64, CPython 3.13.7, ngspice 47 (XSPICE), portable
xschem 3.4.4 and GNU awk 5.4.0 supplied by Git for Windows. No full PDK, WSL, layout toolchain,
cloud service or account is needed. Linux and fresh-OS replication have not been tested.

## 1. Isolated notebook environment

From this project directory, using an existing Python installation:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m unittest discover -v -s . -p "test_*.py"
.venv/Scripts/python validate_notebook.py
```

This convenient range-based route is not the exact tested lock. For the tested Windows x64 /
Python 3.13 dependency set, `requirements-clean-win64.txt` pins every installed dependency with
a wheel SHA-256. The small CACE wheel in `vendor/` was built from the unchanged pinned source.
Download the other wheels once, then install without network:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip download --only-binary=:all: --require-hashes --no-deps -r requirements-download-win64.txt --dest wheelhouse
Copy-Item vendor/*.whl wheelhouse/
.venv/Scripts/python -m pip install --no-index --find-links wheelhouse --require-hashes -r requirements-clean-win64.txt
.venv/Scripts/python -m pip check
.venv/Scripts/python validate_notebook.py
```

The download-only requirements exclude CACE, supplied by the bundled wheel. Installation uses
the complete unchanged hash lock. No package hash should be bypassed.
The clean local validation used the wheelhouse directly and installed all packages offline.
The lock targets this specific Python/platform; it is not a universal Linux lock.

`CLEAN_ENVIRONMENT.json` records package origins and source checks. `CLEAN_REPRODUCTION.json`
records a second isolated environment installed from the hash lock, executing a separate copy
of the package. Both exclude system and user site-packages. This is clean dependency validation
on the same host, not independent verification by another person or on a freshly installed OS.

## 2. Fresh ngspice run

```text
python reproduce.py tt27_continuous_fossi --ngspice /path/to/ngspice
```

On Windows add `--codemodel-dir C:/path/Spice64/lib/ngspice` when needed. See README for native
ngspice settings. Expected nominal delay: approximately 1.125921 ms, VALID/PASS. The old-library
`tt27_continuous_nanoamp` recipe has an INVALID scalar measurement. Under the separately
supplied teaching contract T1 its functional result is FAIL; that is not proof of
violation of the original designer's acceptance specification.
Each run retains its log, input, waveform, provenance and sampled resources.

## 3. Full CACE route

```text
python cace_project.py tt27_continuous_fossi --output-dir C:/short/writable/cace_runs --xschem C:/tools/xschem/bin/XSchem.exe --ngspice C:/tools/Spice64/bin/ngspice_con.exe --codemodel-dir C:/tools/Spice64/lib/ngspice --awk-dir "C:/Program Files/Git/usr/bin"
```

Use actual installed paths; do not create a system-root directory unless it is writable.
`--output-dir` must be short enough for native Windows tools. The project/model paths and
code-model directory should have no spaces for this tested native tool combination.
Use the same command with `tt27_continuous_nanoamp` and `tt27_continuous_fossi_slow` for the
negative control and extended ramp. The notebook also exposes an off-by-default live-run cell.

The command runs unmodified CACE 2.13.0, real xschem, real ngspice and the documented hook.
Expected results: nominal and slow ramp exit 0 / Pass; old library exits 1 / Error with
`Missing por rising event in declared window`. Always inspect the reason; an arbitrary error
does not validate this result. `CACE_INTEGRATION.md` describes what was and was not migrated.

## Integrity and resource budget

`MANIFEST.json` protects evidence, model sources and recipes. `PACKAGE_MANIFEST.json` protects
the release files, including the notebook and Python source; rerunning validation changes the
notebook output/validation records, so verify a distributed archive before regenerating outputs.
The simulator and xschem binaries are not redistributed. Their measured hashes and xschem's
official download URL are recorded with the environment evidence.

Measured downloads added for this stage: about 48.93 MiB of wheels and 22.87 MiB of xschem.
One clean Python environment occupies about 236.8 MiB; xschem about 33.3 MiB. The second
environment is a validation copy, not a runtime requirement. Full CACE runs peaked near
587 MiB for the process tree and took 49–75 seconds. Simulations run serially, request one
numeric thread and use sampled watchdogs (180 seconds, 4 GiB tree RSS, 200 MiB output).
These values are for this small POR setup, not a resource promise for complete EDA flows.

Browser validation used local HTTP. The automation browser blocks file:// URLs, so double-click opening has not yet been tested directly. Self-contained assets are verified in code; record the actual browser and entry mode during the reader trial.
