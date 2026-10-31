# A small experiment before a full chip flow

Start in this project directory. The first exercise needs no model account,
paid service, Python packages, synthesis, physical tools or restored raw evidence.
It tests a concrete design contract: a signed dot product must hold its result
under backpressure and discard cancelled work. The correct result is −7;
the supplied cancellation fault must be rejected.

## Route 1: a clean Linux teaching container (x86-64)

Prerequisites on the host: Podman or Docker, Bash, curl, sha256sum, and Internet
access for the initial build. The script downloads an official Ubuntu Base
24.04.3 root filesystem, checks its fixed SHA-256, and installs Python and Icarus
inside the container. It does not alter the host's Python or EDA installation.
Allow about 1 GB of container space. The Ubuntu archive packages are resolved at
build time; the versions used for validation are recorded in
`toolchain/minimal-environment.json`. This is a teaching environment, not the
pinned historical PPA toolchain.

```bash
bash scripts/build_lesson_container.sh --network host --security-opt seccomp=unconfined
mkdir -p ../chipwave-lesson-output
podman run --rm --network none --read-only --tmpfs /tmp:rw \
  --security-opt seccomp=unconfined --security-opt label=disable \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD:/work:ro" \
  -v "$(cd ../chipwave-lesson-output && pwd):/out:rw" \
  localhost/chipwave-lesson:20261030 \
  python3 -B scripts/handshake_lesson.py --output /out/handshake
```

For Docker, set `CONTAINER_ENGINE=docker` on the build command and replace
`podman` with `docker` for the run. Docker is an alternative command, not a
separately validated runtime here. The explicit security options above are
needed by the validation host's legacy Podman/SELinux setup; they relax the
container syscall/label filters, not host policy. On modern engines, try omitting
those options. The lesson still runs without network access, with read-only
project/root mounts and a writable temporary directory. The build uses the host
network for its loopback proxy; it can be omitted when that proxy is unnecessary.
Rootless containers are recommended. Output ownership follows the engine.

Expected final line includes `"passed": true`, `"delivered_cycles": [6]` and
`"mutant_rejected": true`. Inspect `../chipwave-lesson-output/handshake/lesson.json`
and `reference/trace.csv`: delivery occurs once, and the cancelled result does
not retire. Repeating the exercise requires a new output path; old results are
never overwritten. The run has no network access and starts no AI or physical flow.

## Route 2: existing native Python and Icarus

With Python 3.12, `iverilog` and `vvp` on PATH:

```bash
python3 scripts/handshake_lesson.py --output ../handshake-native
```

## Then change the experiment, not just the circuit

Install the Notebook/runtime dependencies following [README](README.md).
With the recorded Icarus/Yosys-Slang tools from [the toolchain guide](toolchain/README.md):

```bash
python scripts/build_benchmark.py --family counter --width 16 --output ../counter16-task
python scripts/qualify_benchmark.py --task ../counter16-task
python scripts/workflow_tutorial.py --output ../workflow-lessons
```

The first pair builds a typed task, checks its reference and rejects its faults;
physical calibration is a separate step. The tutorial replays saved RTL with
real tool checks and changes roles, dependencies and IP entry. Its output is
labeled replay, not a fresh AI design. The small teaching container intentionally
does not contain Yosys, the full public runtime or the physical tools.

## Full saved-evidence replay

Before the identity lesson, full delivery checks, or workload measurement:

```bash
python scripts/evidence_store.py verify
python scripts/evidence_store.py restore
```

This restores original files from local compressed chunks, including failed
trials. It requires no download. Allow 30 GB free working space for restored
material and measurement scratch. Continue with the replay commands in
Notebook Appendix D. Fresh model experiments require a user-supplied account
and explicit execution; none is needed for the routes above.
