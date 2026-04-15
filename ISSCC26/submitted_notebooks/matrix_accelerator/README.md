
# MAC-Based Systolic Array Accelerator for ML Inference

**Author:** Suliat Saka  
**Institution:** University of Lagos, Electrical and Electronics Engineering  
**License:** Apache 2.0

## Description

A parameterized MAC-based systolic array hardware accelerator for ML inference, implemented in Verilog and synthesized on SkyWater 130nm (Sky130A) using OpenLane.

- Weight-stationary dataflow (same architecture as Google TPU)
- 4×4 systolic array, 16 MAC units
- Verified against numpy golden reference using Icarus Verilog
- Timing closure at 50MHz, zero DRC/LVS violations on Sky130A

## Tools
- Icarus Verilog, GTKWave, OpenLane v1.0.2, Sky130A PDK
