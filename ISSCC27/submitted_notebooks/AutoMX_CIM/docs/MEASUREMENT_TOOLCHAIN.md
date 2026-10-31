# Measurement toolchain and evidence boundaries

Copyright 2026 EDABK Laboratory.

The notebook runs Python from `env_mamba`; its first execution cell prints the actual interpreter. Native workers use that same interpreter. Python dependencies are declared in `environment.yml` and `requirements.txt`. The extracted source-IP check uses a separate virtual environment with the supplied NumPy 1.26.4 wheel and the host Icarus executable.

| Experiment | Tools and libraries | Produced evidence |
|---|---|---|
| Numerical formats and attention | NumPy, Python independent reference, synthesizable SystemVerilog | MXFP4/X2 quantization, ternary signs, softmax approximation, output equivalence |
| Wearable deployment | NumPy, PyTorch, scikit-learn | Frozen subject-separated training/validation/test, confusion matrices, paired subject-bootstrap controls |
| Circuit conversion | Shared ngspice 44.2 library through Python `ctypes`, SKY130 device models; Icarus SAR RTL | Actual comparator decisions, fresh EOC/code, tagged voltage/current samples |
| Physical delivered pulse | Mapped SKY130 transistor-cell models, shared ngspice, child/parent SPEF, OpenSTA clock arrival/slew | Actual loaded wordline levels/widths, quiet-line checks and bitline changes |
| Synthesis and physical implementation | Pinned OpenLane container, Yosys/ABC, OpenROAD/OpenRCX | Mapped cell areas, placed/routed ODB/DEF, actual RC, rails and hierarchical timing |
| Layout/circuit consistency | Magic and Netgen | Extracted topology, macro transistor LVS where run, and top signal macro-boundary LVS |
| Active/idle readout and MHA power | Icarus mapped functional gate simulation, VCD, SKY130 TT Liberty, SPEF, OpenSTA 3.1.0 | Matched activity windows, disjoint instance attribution, child-digital power/energy estimates |
| Calibration clock gate | Actual mapped `dlclkp_1`, VCD edge parser, OpenSTA 3.1.0 | Clock activity at 3,648 data flops and GATE enable setup/hold timing |
| Area/render review | OpenROAD ODB bindings; native KLayout; Pillow | Routed standard-cell area distinct from macro footprint; fixed palette and independent pixel comparison |
| Figures and notebook execution | Matplotlib, pandas, IPython, nbformat, nbclient | Tables/figures from measured reports; complete cell/error/output coverage |

The OpenSTA source revision/build record is `tools/opensta_current/tool.json`; it uses the native `read_vcd` command. Earlier container OpenSTA 2.4 gated-clock estimates are excluded from the adoption decision. A matched comparison uses one version for all its rows.

The KLayout renderer uses the native host program. The foundry-rule check uses the pinned container version with an explicit time bound. A render, router DRC result, transistor LVS result and foundry-deck result describe different checks; one is not substituted for another.

Native transcripts, emitted decks/Tcl, activity and numerical reports remain beside each experiment in the fresh run. Cell outputs show principal measured results. No table requires a hand-entered energy, accuracy or tool-pass value. Conversion energy integrates actual supply/reference samples over START–EOC; gate power uses VCD/Liberty/SPEF estimates. Their ownership windows remain explicit.
