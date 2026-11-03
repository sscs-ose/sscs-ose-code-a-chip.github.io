# nano_hash: A SHA-256 cryptographic hash function hardware accelerator

A synthesizable SystemVerilog implementation of SHA-256 with AXI4-Stream-style message ingress and digest egress. The design accepts a message as 32-bit stream beats, performs FIPS 180-4 message padding and SHA-256 compression, and emits the 256-bit digest as eight 32-bit stream beats.

The repository is organized as a small reusable datapath with standalone unit-level testbenches and a top-level integration testbench.

## Features

- SHA-256 processing with the standard 64-round compression function.
- 32-bit AXI4-Stream-style input interface.
- 32-bit AXI4-Stream-style output interface.
- Byte-valid input beats through `s_axis_tkeep`.
- Automatic `0x80` delimiter and 64-bit message-length padding.
- Single-block and multi-block message support.
- Input-side valid bubbles and output-side backpressure handling.
- Standalone verification for the padder, message scheduler, compression engine, core, serializer, and integrated top level.
- Simulation waveform generation through `waveform.vcd` in the top-level testbench.

## Repository Layout

```text
.
|-- README.md
|-- docs/
|   `-- figures/
`-- src/
    |-- rtl/
    |   |-- digest_buffer.sv
    |   |-- hashing.sv
    |   |-- message_padder.sv
    |   |-- message_scheduler.sv
    |   |-- sha_256_constants.sv
    |   |-- sha_256_top.sv
    |   `-- sha_core.sv
    `-- tb/
        |-- digest_buffer_tb.sv
        |-- hashing_tb.sv
        |-- message_padder_tb.sv
        |-- message_scheduler_tb.sv
        |-- sha_256_top_tb.sv
        |-- sha_core_tb.sv
        |-- tb_constants.sv
        |-- waveform.vcd
        `-- memory_files/
            |-- digest_buffer/
            |-- hashing_core/
            |-- message_scheduler/
            |-- padder/
            |-- round_constants/
            `-- sha_256_core/
```

The repository does not currently include a simulator-specific build script or project file. The testbenches use SystemVerilog features such as `logic`, enumerated states, automatic tasks, clocking blocks, and `$readmemh`; use a simulator with SystemVerilog support.

## Architecture

```text
                 32-bit AXI4-Stream input
                            |
                            v
                 +-----------------------+
                 |   message_padder     |
                 |  buffering + padding  |
                 +-----------------------+
                    512-bit message block
                            |
                            v
                 +-----------------------+
                 |       sha_core        |
                 |                       |
                 |  +-----------------+  |
                 |  | message_scheduler|  |
                 |  | 16-word window  |  |
                 |  +-----------------+  |
                 |          |            |
                 |          v            |
                 |  +-----------------+  |
                 |  |  hashing_core   |  |
                 |  | 64 compression   |  |
                 |  | rounds           |  |
                 |  +-----------------+  |
                 |          ^            |
                 |  +-----------------+  |
                 |  | SHA-256 constants| |
                 |  | 64 round values  | |
                 |  +-----------------+  |
                 +-----------------------+
                       256-bit digest
                            |
                            v
                 +-----------------------+
                 |    digest_buffer     |
                 |  8 x 32-bit output   |
                 +-----------------------+
                            |
                            v
                 32-bit AXI4-Stream output
```

### Top-level: `sha_top`

`sha_top` in `src/rtl/sha_256_top.sv` connects the three externally visible stages:

1. `message_padder` accepts input stream beats and produces complete 512-bit SHA-256 blocks.
2. `sha_core` expands and compresses each block, maintaining the intermediate hash state across blocks.
3. `digest_buffer` captures a completed 256-bit digest and serializes it on the output stream.

The top level combines the core's `digest_valid` indication with the padder's `done` signal. This ensures the digest is exposed to the output serializer only after the final message block has completed.

### Message padder: `message_padder`

The padder buffers up to sixteen 32-bit words. It tracks the message length in bits and implements the SHA-256 padding rule:

```text
message || 1'b1 || zero padding || 64-bit message length
```

The resulting message is emitted as one or more 512-bit blocks, with the first byte placed in the most-significant byte position of each 32-bit word. Its state machine contains the following phases:

- `IDLE`: waits for the first input beat.
- `WRITE_BUFFER`: accepts subsequent message beats.
- `PADDING`: writes the delimiter, zero padding, and length field.
- `BUFFER_FULL`: waits for the SHA core to become available.
- `SEND`: asserts `sha_valid` for the buffered block and handles spillover into a second block.

The padder handles padding that fits in the current block and padding that requires an additional block. The 56-byte integration test specifically exercises this boundary.

### SHA-256 core: `sha_core`

`sha_core` is the internal block-processing unit. It combines:

- `message_scheduler`: loads the sixteen input words and produces the expanded schedule words through a sliding 16-word window.
- `hashing_core`: performs the 64 compression rounds and accumulates the eight 32-bit hash state words.
- `sha_256_constants`: provides the round constant `K[t]` for each round index.

The core accepts a block when `sha_valid` and `scheduler_ready` are both asserted. A new message initializes the hash state with the SHA-256 initial values. Additional blocks use the digest from the preceding block as the chaining state. The `done` input identifies the final block so the core can return to its idle, message-ready state after producing the final digest.

The compression engine is iterative: one round is advanced per clock while in its compression state. It implements the standard `Ch`, `Maj`, capital sigma, and message-schedule functions, then adds the working variables back into the hash state at the end of the block.

### Digest serializer: `digest_buffer`

`digest_buffer` captures the 256-bit digest on a rising edge of `digest_valid` and presents it as eight 32-bit words, most-significant word first:

```text
m_axis_tdata[0] = digest[255:224]
...
m_axis_tdata[7] = digest[31:0]
```

The serializer asserts `m_axis_tvalid` while output data is available and advances only on `m_axis_tvalid && m_axis_tready`. It therefore retains the current word while the downstream consumer applies backpressure. `m_axis_tlast` identifies the eighth and final digest word.

## AXI4-Stream Interfaces

The interfaces follow the AXI4-Stream valid/ready transfer convention:

```text
transfer occurs when tvalid && tready
```

### Input stream

| Signal | Width | Direction | Description |
|---|---:|---|---|
| `aclk` | 1 | input | Shared clock. |
| `aresetn` | 1 | input | Active-low asynchronous reset. |
| `s_axis_tdata` | 32 | input | Message data, packed big-endian within each word. |
| `s_axis_tkeep` | 4 | input | Valid-byte mask for the input word. |
| `s_axis_tvalid` | 1 | input | Input word is available. |
| `s_axis_tlast` | 1 | input | Marks the final input beat of the message. |
| `s_axis_tready` | 1 | output | Padder is ready to accept the input beat. |

In this implementation, the partial-word masks are interpreted as follows:

| `s_axis_tkeep` | Valid bytes | Meaning |
|---|---:|---|
| `4'b1000` | 1 | Most-significant byte is valid. |
| `4'b1100` | 2 | Two most-significant bytes are valid. |
| `4'b1110` | 3 | Three most-significant bytes are valid. |
| `4'b1111` | 4 | All bytes are valid. |
| `4'b0000` | 0 | Used by the empty-message test case. |

This is the convention implemented by `message_padder`; producers must match it. A beat is consumed only when both `s_axis_tvalid` and `s_axis_tready` are high. `s_axis_tlast` must be asserted on the final beat.

### Output stream

| Signal | Width | Direction | Description |
|---|---:|---|---|
| `m_axis_tdata` | 32 | output | Serialized digest word, most-significant word first. |
| `m_axis_tvalid` | 1 | output | Digest word is available. |
| `m_axis_tready` | 1 | input | Downstream is ready to consume the word. |
| `m_axis_tlast` | 1 | output | Identifies the eighth digest word. |

The output consists of exactly eight transfers per digest. If `m_axis_tready` is low, the serializer holds the current word and does not advance its counter.

## Reset and Transaction Behavior

- Reset is active low through `aresetn` at the top level and `rst_n` on the core submodules.
- Reset clears the padder buffer, scheduler window, compression state, digest serializer, and stream status.
- The input stream can begin after reset is released and the padder asserts `s_axis_tready`.
- The padder can accept a new message after the final block has been consumed by the core and `done` returns the datapath to its idle state.
- A message can occupy one or multiple 512-bit blocks. The SHA-256 chaining state is preserved between blocks and reset to the standard initial constants for a new message.

## Verification

### End-to-end verification

`src/tb/sha_256_top_tb.sv` drives the complete `sha_top` design and checks the received 256-bit digest against known SHA-256 reference values. It also checks output framing and flow control.

The five sequences are:

1. **`abc`**, three bytes: verifies a partial final input word using `s_axis_tkeep = 4'b1110` and checks the well-known digest `ba7816...015ad`.
2. **Empty message**: verifies zero-length input handling and the one-block padding boundary, with digest `e3b0c4...b855`.
3. **56-byte message**: forces the delimiter and length field into a second block and checks multi-block chaining, with digest `248d6a...06c1`.
4. **26-byte alphabet message with ingress bubbles**: randomly deasserts `s_axis_tvalid` to verify that the padder preserves message state across input delays, with digest `71c480...8b73`.
5. **`abc` with egress backpressure**: deasserts `m_axis_tready` during output to verify serializer stalling and data retention.

The testbench also verifies that `m_axis_tlast` is low for the first seven output words and high on the eighth word.

### Unit-level verification

| Testbench | Unit under test | Coverage |
|---|---|---|
| `message_padder_tb.sv` | `message_padder` | Stimulus and expected 512-bit blocks loaded from `memory_files/padder`; exercises input valid/last, byte masks, scheduler stalls, and padding/spillover cases. |
| `message_scheduler_tb.sv` | `message_scheduler` | Loads a 16-word block and compares all expanded schedule words against `memory_files/message_scheduler/message.mem`. |
| `hashing_tb.sv` | `hashing_core` | Drives round constants and schedule words from memory files and checks SHA-256 digests for three reference blocks. |
| `sha_core_tb.sv` | `sha_core` | Checks single-block messages, the empty message, the alphabet message, and a two-block message using block vectors in `memory_files/sha_256_core`. |
| `digest_buffer_tb.sv` | `digest_buffer` | Checks serialization of four reference digests into eight words using vectors in `memory_files/digest_buffer`. |
| `sha_256_top_tb.sv` | `sha_top` | Integrates the complete ingress, padder, core, and egress path, including bubbles and backpressure. |

The memory files contain deterministic input vectors, expected padded blocks, message schedule words, round constants, and expected serialized digest words.

## Simulation

Use your simulator's SystemVerilog compile and run flow with the RTL sources and the selected testbench. A representative source list is:

```text
src/rtl/sha_256_constants.sv
src/rtl/message_scheduler.sv
src/rtl/hashing.sv
src/rtl/sha_core.sv
src/rtl/message_padder.sv
src/rtl/digest_buffer.sv
src/rtl/sha_256_top.sv
src/tb/sha_256_top_tb.sv
```

Run simulations from `src/tb` or configure the simulator's working directory so relative `$readmemh` paths resolve to the corresponding `memory_files` directories. The top-level testbench writes `waveform.vcd`; view it with a VCD viewer such as GTKWave after simulation.

For a simulator that supports SystemVerilog clocking blocks, the general flow is:

```text
compile RTL and testbench sources with SystemVerilog enabled
run the selected testbench until $finish
inspect PASS/FAIL output and waveform.vcd
```

The repository does not prescribe a particular simulator command because no Makefile, simulator project, or tool-specific configuration is included.

## Data Ordering

The implementation uses big-endian word ordering at the SHA-256 block boundary:

- The first message byte occupies bits `[31:24]` of the first input word.
- The first block word occupies bits `[511:480]`.
- The digest is emitted from `digest[255:224]` down to `digest[31:0]`.

This ordering is visible in the top-level testbench's byte packing and in the scheduler's block loading logic.

## Design Notes and Limitations

### Module Naming and Hierarchy
* **Top-Level Entity:** The primary synthesizable top-level module is named `sha_top` (not `sha_256_top` or `sha256_top`). All top-level instantiations and testbench bindings must target `sha_top`.

### Interface Semantics
* **Streaming Protocol:** The interface implements an AMBA AXI4-Stream-style point-to-point protocol (`s_axis_*` for payload ingress, `m_axis_*` for digest egress).
* **Omission of Bus Infrastructure:** The core does not include an AXI memory-mapped crossbar/interconnect, register interface (Control and Status Registers / CSRs), address decoding, or burst-control logic.
* **System Integration:** Memory access, scatter-gather buffer descriptors, and packet framing must be handled externally by upstream/downstream DMA engines, streaming FIFOs, or custom bus adapters.

### Datapath Sizing and Throughput
* **Bus Widths:** Ingress data (`s_axis_tdata`) and egress digest data (`m_axis_tdata`) are both fixed to a 32-bit width.
* **Digest Serialization:** The 256-bit output hash is serialized across the egress interface, transmitting one 32-bit word per handshake beat. Draining the complete digest requires 8 valid transfer cycles ($H_0 \dots H_7$).

### Microarchitectural Trade-offs
* **Iterative Architecture:** The design implements a folded, iterative round computation rather than a fully unrolled (cascaded 64-stage) or deeply pipelined execution pipeline.
* **Block Latency:** Computing each 512-bit message block requires the message schedule load phase, 64 iterative compression rounds, and a state accumulation cycle (~66 clock cycles per block).
* **Area vs. Throughput:** This iterative approach significantly minimizes FPGA LUT and flip-flop consumption at the expense of multi-block streaming throughput.

### Implementation and Verification Scope
* **Vendor-Agnostic RTL:** The codebase consists of pure, standard SystemVerilog without vendor-specific macro instantiations or target-locked IP wrappers.
* **Constraints and Reports:** Hardware synthesis constraints (XDC/SDC), static timing closure constraints, post-implementation utilization reports, and formal property suites (SVA/bind files) are not bundled with this repository.
* **IP Packaging:** Vendor-specific packaging metadata (such as Vivado IP-XACT `component.xml` or Intel Platform Designer components) is excluded and must be generated during target system integration.

## References

- NIST, **FIPS PUB 180-4: Secure Hash Standard (SHS)**.
- AXI4-Stream valid/ready transfer semantics as used by the AMBA AXI protocol family.
