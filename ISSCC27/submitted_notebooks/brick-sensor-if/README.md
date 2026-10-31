# Brick Sensor Interface — `brick-sensor-if`

Code-a-Chip (ISSCC27) submission: a verified sensor-interface IP block —
SPI IMU readout + CAN 2.0A frame framer — in synthesizable Verilog,
targeting the open SkyWater 130 nm PDK. The same RTL is planned for
Tiny Tapeout TTSKY26d (after this notebook submission).

## Contents

- `brick_sensor_if.ipynb` — the submission notebook (narrative + runnable cells)
- `rtl/` — Verilog: `brick_sensor_if.v` (top + register file), `spi_master.v`, `can_framer.v`
- `golden/` — `can_golden.py`: bit-exact Python model of the CAN framer
- `tb/` — cocotb testbench (`make` in this dir to run; needs Icarus Verilog + cocotb)
- `synth.ys`, `run_synth.sh` — Yosys synthesis for `sky130_fd_sc_hd` (needs Volare PDK)
- `LICENSE` — Apache-2.0

## Quick start

```bash
pip install cocotb volare
volare fetch --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b
volare enable --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b
(cd tb && make)        # simulation: 13 cocotb tests
./run_synth.sh        # synthesis: area/cell report in synth/synth.log
```

Or open `brick_sensor_if.ipynb` and run top to bottom.
