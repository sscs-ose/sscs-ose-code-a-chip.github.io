# JS-SoC — Code-a-Chip

JS-SoC is a SystemVerilog-based RV32I System-on-Chip (SoC) featuring a hardware bootloader and an APB-based peripheral subsystem.

## Included

- Complete `SoC_V3` RTL
- RV32I CPU core
- Hardware bootloader
- Instruction memory (IMEM)
- Data memory (DMEM)
- CPU control and datapath
- APB bridge/master and FIFO infrastructure
- UART peripheral
- PWM peripheral
- Timer peripheral
- System-level SystemVerilog testbench
- 22-instruction bootloader demonstration
- Reproducible Icarus Verilog simulation script
- Simulation log and waveform evidence
- Vivado cross-verification waveforms for the bootloader, UART, Timer, PWM and integrated SoC
- Open-source RTL-to-GDSII implementation on Sky130HD (Yosys + OpenROAD), 0 DRC markers
- Jupyter notebook documenting the architecture, verification and physical-design flow

## Repository Structure

```text
JS-SoC-Code-a-Chip/
├── README.md
├── LICENSE
├── rtl/
│   └── SystemVerilog RTL files
├── tb/
│   └── top_tb.sv
├── programs/
│   └── bootloader_demo.hex
├── scripts/
│   └── run_sim.sh
├── docs/
│   ├── soc_block_diagram.png
│   └── soc_architecture.png
├── results/
│   ├── bootloader_writing.png
│   ├── execution.png
│   ├── simulation_log.txt
│   ├── build/
│   │   └── js_soc.vcd
│   ├── vivado/          # Vivado waveforms and APB FSM
│   └── openroad/        # Sky130HD layout views
└── notebook/
    └── JS_SoC_Code_a_Chip.ipynb
```

## Quick Start

From the submission root:

```bash
./scripts/run_sim.sh
```

The script compiles the RTL and testbench using Icarus Verilog and runs the resulting simulation.

## Manual Simulation

Compile:

```bash
iverilog -g2012 -s cpu_tb -o results/build/simv rtl/*.sv tb/top_tb.sv
```

Run:

```bash
vvp results/build/simv
```

## Verification

The SoC was verified using the provided SystemVerilog testbench with Icarus Verilog.

The testbench verifies the bootloader programming sequence, instruction memory contents, bootloader state, and CPU register results using `$fatal` assertions.

### Verified Results

The simulation successfully verified:

- Bootloader received and processed 22 instructions.
- Bootloader released the CPU after programming.
- Instruction memory was populated with the expected instruction sequence.
- CPU execution produced the expected register values.
- Simulation completed successfully with `SIMULATION PASS`.
- A VCD waveform was generated at `results/build/js_soc.vcd`.
- The complete simulation output is recorded in `results/simulation_log.txt`.

### CPU Register Results

| Register | Value |
|----------|-------|
| x0 | `0x00000000` |
| x1 | `0x0000000F` |
| x2 | `0x00000014` |
| x3 | `0x00000023` |
| x4 | `0x00000014` |
| x5 | `0x00000037` |
| x6 | `0x0000002D` |
| x7 | `0x00000000` |

The bootloader successfully received 22 instructions, with an instruction count of 22. The bootloader completed with `HOLD = 0` and `SEL = 0`.

## Waveform Evidence

Two waveform screenshots are included in the `results/` directory:

- `bootloader_writing.png`
- `execution.png`

The complete simulation waveform is available as:

```text
results/build/js_soc.vcd
```

The VCD file can be opened using a waveform viewer such as GTKWave.

## Simulation Output

The complete output from the verified simulation is provided in:

```text
results/simulation_log.txt
```

The log includes the bootloader completion status, instruction memory contents, CPU register results, and final `SIMULATION PASS` message.

## Demonstration Program

The included testbench sends a 22-instruction RV32I demonstration program to the hardware bootloader.

The bootloader receives the program as 8-bit data, assembles the instruction words, and writes them into instruction memory. After programming is complete, the CPU is released to execute the loaded instructions.

## License

This project is released under the **Apache License 2.0**. See the `LICENSE` file in the repository root for the complete license text.

## Notebook

The Jupyter notebook:

```text
notebook/JS_SoC_Code_a_Chip.ipynb
```

provides a detailed walkthrough covering:

- Project overview
- System architecture
- RTL organization
- Hardware bootloader
- Demonstration program
- Verification methodology
- Simulation flow and live register-file checks
- Vivado cross-verification
- Open-source RTL-to-GDSII on Sky130HD (OpenROAD-flow-scripts, run on Google Colab)
- Results summary, reproducibility and conclusion

## Physical Design

Implemented on SkyWater Sky130HD with the open-source OpenROAD-flow-scripts:

| | Sky130HD |
|---|---|
| Flow | Yosys, OpenROAD (ORFS), KLayout |
| Clock | 35 MHz |
| Die | 624 × 624 µm |
| Timing | No setup/hold violations |
| DRC | 0 (router) / 0 (KLayout) |

Details, logs and layout views are in Section 7 of the notebook.

## Submission Scope

Only the working `SoC_V3` design is included in this submission. Older experimental versions and unrelated development artifacts from the original repository are intentionally excluded.

## Reproducibility

The simulation can be reproduced using Icarus Verilog with:

```bash
iverilog -g2012 -s cpu_tb -o results/build/simv rtl/*.sv tb/top_tb.sv
vvp results/build/simv
```

Alternatively:

```bash
./scripts/run_sim.sh
```

The generated VCD waveform will be written to:

```text
results/build/js_soc.vcd
```