# Zenith Core — Code-a-Chip ISSCC 2027 submission

**Author:** Pablo José López Mazariegos (Guatemala)
**License:** Apache License 2.0 (see `LICENSE`)
**Notebook:** [`Zenith_Core.ipynb`](Zenith_Core.ipynb)

Zenith Core is an 8-bit, RISC-V-inspired microcontroller designed from scratch in Verilog (16-bit ISA, 6-state multi-cycle CPU, memory-mapped GPIO/UART/PWM) together with its own toolchain: an assembler, a UART loader that writes programs straight into instruction memory without re-synthesising the FPGA, a graphical IDE and a simulation front-end. It has been validated on a Sipeed Tang Nano 9K FPGA.

The notebook is fully reproducible **without any hardware**. It assembles four demo programs (a counter, a UART transmitter, a PWM and a Fibonacci sequence), loads each one through the serial protocol in an Icarus Verilog simulation (the testbench plays the role of the host PC at 115200 baud), and decodes the resulting waveforms: the loading protocol, the CPU state machine (CPI and MIPS measured from the waveform), the UART transmitter and the PWM. The Fibonacci example follows one program through the whole chain: source, machine code, bytes on the wire, instruction-memory contents read back after the load, disassembly, and execution. The same program is then run from a hex file in a second testbench and under cocotb, and the graphical tools (JoJoP IDE and the simulation front-end) are shown with screenshots.

## Run it

* **Google Colab / Jupyter:** open `Zenith_Core.ipynb` and run all cells. The first cells install Icarus Verilog and a few Python packages. If the notebook is opened outside a clone of this folder, it fetches this folder from the Code-a-Chip repository automatically.
* **Requirements:** Python 3.9+, `pip install -r requirements.txt`, and Icarus Verilog (`iverilog` + `vvp`) on the PATH — Windows installer from <https://bleyer.org/icarus/>, `apt-get install iverilog` on Ubuntu/Colab, `brew install icarus-verilog` on macOS. GTKWave can open the generated `.vcd` files for interactive inspection.

## Contents

| Path | Description |
|---|---|
| `Zenith_Core.ipynb` | The notebook (executed, with outputs) |
| `requirements.txt` | Python packages |
| `rtl/` | Verilog source of the CPU, memories, peripherals, UART loader and Tang Nano 9K top level / pin constraints |
| `tools/assembler.py` | Two-pass assembler (`.hex` for simulation, `.bin` for the serial loader) |
| `tools/uart_flash.py` | Host-side flashing tool for the real board |
| `sim/tb_flash.v` | Testbench that acts as the host PC in the serial loading protocol |
| `sim/tb_fibo.v` | Testbench that loads a `.hex` file into the instruction memory and checks the Fibonacci output |
| `sim/cocotb/` | cocotb tests for the CPU and the Fibonacci program, and the scripts that plot their results (optional, `pip install cocotb`) |
| `programs/` | The four demo programs used in the notebook |
| `imgs/` | Block diagram and screenshots of the graphical tools, the simulations and Gowin EDA |

The full project, including the graphical IDE and further documentation, lives at <https://github.com/PabloJLM/Zenith-Core>.

## Known limitations

Documented in section 10 of the notebook: memory-mapped *reads* return 0 in simulation, immediates are limited to 4-bit signed values, and synthesis for the FPGA uses the (free, not open-source) Gowin EDA; a Yosys flow is future work.
