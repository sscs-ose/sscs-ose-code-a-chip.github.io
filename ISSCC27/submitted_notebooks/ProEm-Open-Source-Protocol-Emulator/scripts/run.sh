#!/bin/bash
# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/run.sh
# Type: Script: build and run every test, then synthesis
# Author: Paul Vincent Bezzina
# Language: Bash
# Description:
# =============================================================================
set -e
cd "$(dirname "$0")/.."
RTL=$(grep -v '^//' src/files.f | tr '\n' ' ')
YOSYS=${YOSYS:-$(command -v yosys || command -v yowasp-yosys)}
SIMYOSYS=${SIMYOSYS:-$(command -v yowasp-yosys || echo $YOSYS)}
RT=${CXXRTL_RUNTIME:-$(python3 -c "import yowasp_yosys,os;print(os.path.join(os.path.dirname(yowasp_yosys.__file__),'share/include/backends/cxxrtl/runtime'))" 2>/dev/null || echo "$($YOSYS-config --datdir)/include/backends/cxxrtl/runtime")}
TESTS="t_control t_uart t_spi t_i2c t_ps2 t_ethernet t_manchester t_usb t_random t_i2c_target t_branch t_stream t_random_branch t_crc t_standards t_modes"
mkdir -p build
$SIMYOSYS -q -p "read_verilog -sv $RTL; hierarchy -check -top protocol_emulator; proc; flatten; memory -nomap; opt; write_cxxrtl build/emu_sim.h" 2>&1 | grep -v "Replacing memory\|feedback" || true
for t in $TESTS; do g++ -std=c++14 -O2 -I"$RT" -Ibuild sim/$t.cpp -o build/$t; done
echo "== control: auto-baud, errors, HALT, CLEAR, LINK, watchdog"
for r in 16 7; do ./build/t_control $r; done
echo "== UART full duplex (sender 2% fast, then 2% slow)"
./build/t_uart 16 40.8; ./build/t_uart 8 39.2
echo "== SPI controller full duplex and SPI target (SCK half period 4, 6, 12 clocks)"
for d in 4 6 12; do ./build/t_spi $d; done
echo "== I2C controller with a device model (SCL half period 4, 10, 25 clocks)"
for d in 4 10 25; do ./build/t_i2c $d; done
echo "== PS/2 device to host"
for h in 40 12; do ./build/t_ps2 $h; done
echo "== 10BASE-T receive, Manchester decoded on chip (50 and 60 MHz)"
for m in 50 60; do ./build/t_ethernet $m; done
echo "== Manchester transmit, looped back into the other chain (6 and 10 clocks per bit)"
for d in 6 10; do ./build/t_manchester $d; done
echo "== USB low speed receive, transmit and loopback"
./build/t_usb
echo "== randomised programs, 150 per seed"
for m in 0 1; do for s in 1 2 3 4 5 6; do ./build/t_random $s $m 150; done; done
echo "== I2C target: address match, branch on R/W, repeated START (SCL at 417 kHz and 1 MHz)"
for h in 60 25; do ./build/t_i2c_target $h; done
echo "== BRANCH: SWD-style ACK handling and CAN-style arbitration"
./build/t_branch
echo "== DATA streamed during a frame, and underrun"
./build/t_stream
echo "== randomised branch programs, 100 per seed"
for m in 0 1; do for s in 1 2 3; do ./build/t_random_branch $s $m 100; done; done
echo "== CRC: USB CRC16 and CRC5 with ACK reply, CAN CRC-15 with stuffing and ACK slot, random CRCs"
./build/t_crc 60
echo "== 16 more standards: RS-485, MIDI, NMEA 0183, PROFIBUS, Modbus, DMX512, LIN, K-Line, SDI-12, SMBus, MDIO, SD card, 3-wire SPI, DALI, CAN 2.0B, RC5"
./build/t_standards
echo "== SPI controller in all four modes (half period 3 and 6 clocks), both BRANCH rules, NOP"
for d in 3 6; do ./build/t_modes $d; done
if [ -n "$SKIP_SYNTH" ]; then exit 0; fi
for top in frame_chain line_codec protocol_emulator; do
  if [ -n "$LIBERTY" ]; then
    $YOSYS -p "read_verilog -sv $RTL; synth -flatten -top $top; check -assert; dfflibmap -liberty $LIBERTY; abc -liberty $LIBERTY; opt_clean; tee -o build/area_$top.txt stat -liberty $LIBERTY" > build/synth_$top.log 2>&1
  else
    $YOSYS -p "read_verilog -sv $RTL; synth -flatten -top $top; check -assert; tee -o build/area_$top.txt stat" > build/synth_$top.log 2>&1
  fi
  echo "== synthesis, $top"; grep -E " cells$|Number of cells|Chip area" build/area_$top.txt
done
