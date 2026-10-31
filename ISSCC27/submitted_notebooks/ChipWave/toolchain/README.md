# Recorded tools and portable flow inputs

The used ORFS Makefile, scripts, utilities and Sky130HD platform files are
bundled in `orfs/`. All 160 copied files were compared against the pinned
upstream checkout; its exact revision, file hashes and scope are in
`orfs/source-manifest.json`. Other platforms and design examples
are not part of this distribution.

A bundled-flow replay exposed an omitted common adder-mapping source. It has
been restored byte-for-byte from the same upstream revision; the diagnosis and
repair are preserved in `results/ppa-bundle-repair.json`. PPA comparisons use
the corrected bundle consistently.

| Executable prerequisite | Version measured for this case | Upstream source |
|---|---|---|
| Python | 3.12.15 | https://www.python.org/ |
| C++ simulation compiler | GCC 13, coroutine support required | https://gcc.gnu.org/ |
| Icarus Verilog and vvp | 13.0, tag `v13_0` | https://github.com/steveicarus/iverilog |
| Verilator | 5.048 | https://github.com/verilator/verilator |
| Yosys with Slang available at startup | 0.69+77, revision `9ff27d29c` | https://github.com/YosysHQ/yosys |
| OpenROAD | revision `4a7cf9b` | https://github.com/The-OpenROAD-Project/OpenROAD |
| KLayout | 0.30.12 | https://www.klayout.de/ |
| Model executor for opt-in AI trials | Codex CLI 0.162.1 | https://github.com/openai/codex |
| Linux model-process isolation | Bubblewrap 0.3.0 | https://github.com/containers/bubblewrap |

Use the upstream installation/build instructions for the recorded source
revision. The executables are external prerequisites, not copies of the
original user's Python environment or commercial EDA tools. `read_slang` must
be available to the Yosys command used by the flow. Check it with
`yosys -Q -p 'help read_slang'` before physical setup.

Before the CPU suite, verify that `g++ --version` selects GCC 13, rather than
an older system compiler. Verilator's timing mode needs its C++ coroutine support.
Activate the matching compiler environment as well as the EDA executables; merely
putting `verilator` on PATH is insufficient. On RHEL with GCC Toolset 13 installed,
this is `source /opt/rh/gcc-toolset-13/enable`.

From the submitted project directory, point the backend to the bundled flow:

```bash
export ORFS_ROOT="$(pwd)/toolchain/orfs"
export CHIP_NEBULA_RTL2GDS_TOOL_ROOT="/path/to/your/pinned-tool-bundle"
export PATH="$CHIP_NEBULA_RTL2GDS_TOOL_ROOT/bin:$PATH"
python -m pip install -r runtime/requirements.lock.txt
python -m pip install ./runtime
python scripts/reproduce.py --output ../independent-functional-run
python scripts/reproduce.py --output ../independent-gds-run --physical
```

The tool bundle's `bin/` supplies `iverilog`, `vvp`, `verilator`, `yosys`,
`openroad` and `klayout`. They may be native executables or transparent
container wrappers. A container wrapper must mount the new project directory
and the bundled flow at the same paths seen by its command. The original
machine needed this mount correction; it is documented in the evidence.
Wrappers must return genuine version output and exit status.

The physical wizard records actual tools and exact source inputs before the
tool task is frozen. Version mismatches, missing inputs, a failed checker,
nonzero DRC, unmatched LVS or timing violations fail acceptance. A different
toolchain is a new experiment and must not inherit the recorded measurements.

The independent rebuild measured in this submission uses a new project
directory and isolated Python environment on the same machine, with the
existing recorded EDA binaries. A fresh operating-system installation was not
measured. Third-party terms are listed in the root notices and `licenses/`.

The bundled KLayout DRC deck explicitly sets `FEOL=false`, `BEOL=true` and
`OFFGRID=true`. A clean result means no violations under these enabled rules,
not full foundry signoff. DRC and LVS retain their recorded four-thread defaults;
`NUM_CORES=2` controls OpenROAD, not a machine-wide CPU quota. The DRC runset
declares GPLv3 in its original header; `licenses/GPL-3.0.txt` supplies the license
text. Standard-cell material and other tools keep their separate upstream terms.

## A smaller starting environment

[QUICKSTART](../QUICKSTART.md) builds a separate Ubuntu/Python/Icarus teaching
container from a checksum-pinned official root filesystem. Its network-disabled
run checks a signed dot product, backpressure and cancellation; it starts no
model or physical flow. See `minimal-environment.json` for its validation receipt.
The [ChipWave tag replay](chipwave-lesson-validation.json) checks the same image
against the renamed project. This closes the minimal-example setup path, not fresh-OS reproduction of the
entire historical EDA toolchain. Before full saved-evidence replay, run
`python scripts/evidence_store.py restore` from the project directory.
