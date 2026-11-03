<a id="references"></a>

## References

**[1]** <a id="ref-1"></a>A. Vaswani et al., [“Attention Is All You Need,”](https://arxiv.org/abs/1706.03762) 2017, arXiv:1706.03762. Source for scaled dot-product attention and multi-head Q/K/V/O equations.

**[2]** <a id="ref-2"></a>Open Compute Project, [*OCP Microscaling Formats (MX) Specification*, Version 1.0,](https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf) September 2023, §§5.2, 5.3.3, 5.4.1. Source for MXFP4 blocks, E2M1 elements, and E8M0 shared scales. The notebook documents its own quantizer tie policy beside the codec.

**[3]** <a id="ref-3"></a>F. Li et al., [“Ternary Weight Networks,”](https://arxiv.org/abs/1605.04711) 2016, arXiv:1605.04711. Background on scaled −1/0/+1 weight representations; the project defines its own transistor-control encoding and 8T netlist.

**[4]** <a id="ref-4"></a>Analog Devices, [“Understanding SAR ADCs: Their Architecture and Comparison with Other ADCs,”](https://www.analog.com/en/resources/technical-articles/successive-approximation-registers-sar-and-flash-adcs.html) October 2, 2001. Background for sample/hold, trial DAC codes, comparator decisions, and SAR-register updates.

**[5]** <a id="ref-5"></a>SKY130_SAR-ADC1 project, [*Fully differential asynchronous non-binary 12-bit SAR ADC in SKY130*.](https://github.com/efabless/SKY130_SAR-ADC1) Reused ADC circuit, SAR control, decoder, and oversampling RTL; the repository identifies its [iic-jku upstream](https://github.com/iic-jku/SKY130_SAR-ADC1). Local sources and retained licenses are documented in `NOTICE.md` and `third_party/SKY130_SAR_ADC1/`.

**[6]** <a id="ref-6"></a>SkyWater SKY130 PDK, [*Physical & Design Verification documentation*.](https://skywater-pdk.readthedocs.io/en/main/verification.html) Process context for device models, layout rules, extraction, and physical verification. Bundled process inputs are identified in `standalone.json` and supplied under `pdks/`; retained upstream license texts are in `licenses/`.

**[7]** <a id="ref-7"></a>ngspice project, [*Documentation and User's Manual*.](https://ngspice.sourceforge.io/docs.html) Transistor-level DC/transient analysis, measurements, and shared-library co-simulation interfaces.

**[8]** <a id="ref-8"></a>Icarus Verilog project, [*Icarus Verilog documentation*.](https://steveicarus.github.io/iverilog/) `iverilog` compilation and `vvp` execution for SAR/controller/MHA tests and state-trace replay.

**[9]** <a id="ref-9"></a>YosysHQ, [*Yosys documentation*.](https://yosyshq.readthedocs.io/projects/yosys/en/latest/) RTL synthesis, hierarchy checks, Liberty technology mapping, and mapped-cell statistics.

**[10]** <a id="ref-10"></a>M. Shalan and T. Edwards, “Building OpenLANE: A 130nm OpenROAD-based Tapeout-Proven Flow,” ICCAD, 2020; publication and flow sources listed in the [official OpenLane repository](https://github.com/The-OpenROAD-Project/OpenLane#publication). Used for the RTL-to-GDS implementation flow; the executed container image is recorded in `standalone.json`.

**[11]** <a id="ref-11"></a>The OpenROAD Project, [*OpenROAD documentation*](https://openroad.readthedocs.io/en/latest/) and [*Parasitics Extraction — OpenRCX*.](https://openroad.readthedocs.io/en/latest/main/src/rcx/README.html) Physical implementation, routed databases, and extracted resistance/capacitance exported as SPEF.

**[12]** <a id="ref-12"></a>The OpenROAD Project, [*OpenSTA*.](https://github.com/The-OpenROAD-Project/OpenSTA) Liberty/SDC/SPEF-based timing analysis, including the hierarchical gate-netlist checks used here.

**[13]** <a id="ref-13"></a>KLayout project, [*KLayout documentation*.](https://www.klayout.de/doc/) GDS hierarchy/geometry inspection, layer-controlled rendering, and scripted layout checks.

**[14]** <a id="ref-14"></a>T. Edwards and contributors, [*Magic VLSI Layout Tool*.](https://github.com/RTimothyEdwards/magic) Layout/extraction tooling, including the DEF/LEF signal extraction used for the top-level LVS comparison.

**[15]** <a id="ref-15"></a>T. Edwards and contributors, [*Netgen*.](https://github.com/RTimothyEdwards/netgen) SPICE/Verilog netlist comparison and LVS verdicts.

The CIM transistor topology, controller/readout integration, MHA RTL IP, and experiments are documented by the source cells and their adjacent measurements. External sources above provide numerical background, reused IP, process information, and tool documentation. Measured voltages, energies, areas, and timing values come from this notebook's logs and reports.

Copyright 2026 EDABK Laboratory.
