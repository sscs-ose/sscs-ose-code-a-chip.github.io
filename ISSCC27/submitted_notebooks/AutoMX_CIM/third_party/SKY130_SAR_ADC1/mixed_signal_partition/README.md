# Pinned mixed-signal partition sources

Unmodified selected files from [efabless/SKY130_SAR-ADC1](https://github.com/efabless/SKY130_SAR-ADC1), commit `892272208df28b6c7620101e129a9d8dd95ebab7` (same revision as the integrated ADC macro). `provenance.json` records the upstream Git blob and SHA-256 of each file. Licensing follows the parent IP's Apache-2.0 license; original file notices are retained.

The executable backend is `scripts/flow2_rtl_spice_cosim.py`: Icarus runs the original SAR controller/decoder/OSR, coupled through the official ngspice shared-library interface to the schematic transistor input switch/comparator and existing CIM acquisition/conditioner.

The XSPICE digital files are retained as pinned reference and for diagnostic probes; the successful final backend uses the original Verilog RTL. It does not use an arithmetic ideal ADC quantizer.

Functional approximations are explicit: exact linear aggregation of the 515 schematic signal capacitors per side (1.4848pF); ideal bottom drivers controlled by real RTL decoder states; external ideal VCM and phase clock; omitted comparator noise-decoupling varactor cards after native charge-model convergence failures. MOS/MIM comparator and input-switch devices are retained. This is not full-chip transistor/PEX/noise/PVT qualification or asynchronous-clock/reference-startup verification.

The co-simulation API follows the [official ngspice header](https://github.com/ngspice/ngspice/blob/master/src/include/ngspice/sharedspice.h). Native phase pauses are expected: each `stop when time`/resume must reach the requested phase boundary; incomplete trajectories and unresolved comparator levels fail the conversion.
