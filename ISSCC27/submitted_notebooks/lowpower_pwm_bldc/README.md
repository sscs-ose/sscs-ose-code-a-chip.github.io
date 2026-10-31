# Low-Power PWM Controller with Dead-Time for BLDC Motor Drives

Code-a-Chip ISSCC 2027 submission by Syed Uzair Ghous Ali.

A small PWM controller for one half-bridge of a BLDC motor driver, written in Amaranth HDL and checked with an open-source flow (Yosys + nextpnr on a Lattice ECP5 FPGA):

_**complementary outputs with programmable dead-time (0 shoot-through cycles in a full sweep)
glitch-free duty updates
clock-enable gating that cuts register switching activity by up to about 90% when the motor is idle**__
_

Open `lowpower_pwm_bldc.ipynb` in Google Colab or Jupyter, uncomment the `pip install` line, and run all cells.

License: Apache 2.0 (see `LICENSE`).
