# openram_energy: energy per cycle and clock-to-output delay of an OpenRAM SKY130 macro, from its transistors

OpenRAM's Liberty views of SKY130 macros are analytical, and their power values are not physical (megawatts for a single
macro). This tool simulates the macro's own transistor netlist in ngspice and reports what an idle, a write and a read
cycle cost, checking every read against the data written. On request it also measures, for every read, the time from
the falling clock edge to the output's crossing of half the supply, at a chosen process corner, supply and temperature.

| File | Role |
|:---|:---|
| `openram_energy.py` | builds the deck from the macro's subcircuit pins (one or two ports, with or without a spare column) and parses the ngspice log into energies, read checks and delays |
| `run_openram_energy.sh` | one ngspice process per macro: units for the SKY130 models, the deck, the run, the parse |
| `test_openram_energy.py` | six tests on synthetic netlists and logs (`python3 -m pytest -q`) |
| `second_design/` | the evidence on a macro HSKEM does not use (results, OpenRAM configuration and logs) |

```bash
PDK_LIB=<sky130A>/libs.tech/ngspice/sky130.lib.spice NGSPICE=<ngspice 41+ with KLU> \
  run_openram_energy.sh <work dir> <macro>.sp[.gz] [<macro> ...]          # -> <work dir>/<macro>/energy.json
SRAM_ENERGY_DELAY=1 SRAM_ENERGY_CORNER=ss SRAM_ENERGY_VDD=1.6 SRAM_ENERGY_TEMP=100 run_openram_energy.sh ...
```

Port 0 is exercised: idle cycles, writes of random data to random addresses, then reads of the same addresses; a second
read port is held idle. The energy of a cycle is the supply voltage times the supply charge from one rising clock edge to
the next. Other settings: clock period, idle cycles before the first write, number of accesses, repeated reads of one
address, and the transient tolerance (`SRAM_ENERGY_*`, listed in `openram_energy.py`). The PDK's special devices of newer
bitcells are included from `libs.ref` only when the tech library does not already include them (a second include breaks
ngspice).

## Evidence

- **HSKEM (the design the tool was written for):** the eight macro types of the chip (12 to 24 bits, 128 to 768 words):
  energies of `results/fullchip/sram_energy.json`, flat-layout wiring factors, and clock-to-output delays at the
  sign-off corners (for example 2.05 ns at tt and 3.76 ns at ss for the 12 x 256 macro).
- **A macro HSKEM does not use:** an 8 x 32 macro generated with the same OpenRAM (`second_design/`, 78 s per run). With
  one word per row every read returns the data written; write 10.8 to 11.8 pJ, read 9.1 to 9.5 pJ, idle 2.1 to 3.1 pJ,
  clock to output 1.50 ns at tt.
- **It catches a broken macro:** the same 8 x 32 size with OpenRAM's own choice of words per row returns 2 where 3 was
  written. Reading that word three times returns 2 every time, so the write is what fails. A tighter tolerance and more
  idle cycles do not change it. The macro without column multiplexing stores and returns every word
  (`second_design/README.md`).

Limits: the energies are of the schematic netlist unless a flat layout extraction is given (the wiring factor is then
measured per macro); only port 0 is exercised; the delay is the output's, not the input setup or hold of the address and
data pins. A large macro built from the PDK's special devices (for example the public 1 KB two-port macro) is supported,
but ngspice took more than 1.5 hours to build its circuit, so it is not part of the evidence.

SPDX-License-Identifier: Apache-2.0
