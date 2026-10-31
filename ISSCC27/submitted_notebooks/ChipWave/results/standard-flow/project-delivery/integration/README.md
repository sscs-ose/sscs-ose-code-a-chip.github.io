# CPU/NPU integration

The immutable RTL snapshot `artifact-f978147dc8244ed0b8867cbe299baac9` supplies
`nebula_npu_dot4`, `rv32i_five_stage_cpu`, and `nebula_cpu_npu_top`. All three
files are preserved byte for byte. The top exposes exactly the CPU's 27 ports
and instantiates `core` with `ENABLE_XNEBULA=1`; the CPU's enabled generate branch
instantiates one NPU. No additional RTL wrapper is needed.

`design.f` is the ordered production filelist, relative to the repository root.
It contains only these three frozen files, with the NPU before its CPU caller.
There is no external vendor RTL dependency. `dependencies.lock.json` records
the exact component Artifact set, each consumed project RTL path and hash, and
the frozen Sky130HD TT platform installation. Its 20 technology view records
retain the frozen installation paths and add file sizes and SHA-256 hashes.
They are downstream technology dependencies, not simulation source files.
No foundry assets are copied into this Artifact. Downstream tools must resolve
these paths through `physical/chip-nebula/implementation.constraints.json` and
revalidate the lock before use.

`address_map.json` describes the two external 256 KiB images at
`0x80000000..0x8003ffff` on separate instruction and data interfaces, including
the environment's `tohost` word at `0x8003f000`. Address decoding and access-error
responses belong to the external environment. The NPU has no MMIO address:
`xdot4` writes two operands through its internal request interface and reads the
result through normal CPU register writeback. The instruction port supports
reads only. The physical top contains neither instruction nor data memory;
the frozen memory macro set and required macro views are both empty. The
architectural 32x32 register file retains its approved flop implementation.

Reproduce from the repository root in one shell:

```sh
source /tmp/chipnebula-pinned-tools/env.sh
source /opt/rh/gcc-toolset-13/enable
python3 -B integration/check_integration.py
```

The checker compares every captured input path to its immutable Git revision,
checks the exact port list, ordered filelist and lock, verifies all installed
views, then runs Verilator 5.048 lint, JSON elaboration and the smoke simulation.
The upstream `UNUSEDSIGNAL` waiver is retained for shared decode/payload fields;
the simulation build also waives missing RTL timescales. Other warnings remain
fatal. `build/integration/report.json` records the engineering verdict and links
the tool logs and elaborated hierarchy.

The smoke uses a 16-instruction program and **10 directed transactions**: nine
external data request/response pairs and one NPU request/response pair. Setup
instructions and automatic instruction fetches are not additional directed
target transactions. It checks a 300 ns reset pulse and release 50 ns after the
previous rising clock edge, the first fetch at reset PC, data read/write,
lane-1 byte masking with neighboring bytes preserved, NPU operands, response
at acceptance+2, normal NPU writeback, result store/readback, `tohost` write/read,
and an external error response at address zero. Exactly 15 normal retirements
and one precise cause-5 load trap are required; final data and transaction
ownership must agree. The environment uses three scalar data words and a
read-only instruction case function, all outside the production filelist.

This is local integration evidence with zero formal common acceptance coverage.
Full functional/performance acceptance, formal equivalence, synthesis, STA,
PnR and DRC/LVS remain downstream; this result makes no physical closure claim.
