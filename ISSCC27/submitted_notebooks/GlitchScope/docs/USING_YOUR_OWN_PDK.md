# Using GlitchScope with your own (private) PDK

GlitchScope is library-independent: it reads any Liberty file and any structural
Verilog netlist mapped to that library. Everything runs locally. Nothing is uploaded,
and nothing from your PDK needs to enter this repository.

> **Confidentiality.** Liberty files, SPICE models, netlists and the reports derived from them
> are usually covered by your foundry NDA. Keep them, and the calibration files GlitchScope
> writes for them, outside any public repository. Add your calibration directory
> (`glitchscope/data/<your library name>/`) to `.gitignore`, and only publish results your NDA
> allows.

## 1. Glitch analysis with your Liberty file (no SPICE needed)

```bash
glitchscope --netlist my_block.v --vcd my_tb.vcd --lib my_lib_tt.lib --out report/
glitchscope --netlist my_comb.v --random-vectors 500 --lib my_lib_tt.lib.gz --out report/
```

What GlitchScope takes from the Liberty file:

* **Cell logic** comes from each cell's `function`. Any cell names work, and the full Liberty
  Boolean syntax is supported.
* **Flip-flops** come from `ff` groups: any pin names, Q and/or QN outputs, and async
  clear/preset (applied at the clock edge).
* **Not yet supported:** latches, scan flops (`next_state` with a mux) and negative-edge
  flops. These stop with a clear message.
* **Timing** uses NLDM delay and slew tables. Units are read from the library.
* **Energy** uses `internal_power` tables plus ½CV²:
  * `nom_voltage` sets VDD;
  * energy units are `capacitive_load_unit` × `voltage_unit`².
* **Physical cells** without outputs (tap, fill, decap, diode, endcap) are skipped, and tie
  cells become constants.
* **Clock trees** are recognised by tracing from the flop clock pins back to the clock port.
* **Several Liberty files per corner:** merge them into one file. `scripts/prep_libs.py` shows
  how (it keeps the first header and appends the other files' cells).

Without a SPICE calibration for your library, M2 falls back to M1 (inertial filtering)
for every cell. The report says so (`calibration: none`).

## 2. SPICE pulse calibration (M2) with ngspice

Describe your PDK in a JSON file:

```json
{
  "name": "my65_tt_1v2",
  "liberty": "/secure/pdk/lib/my65_sc_tt_1p2v_25c.lib",
  "cell_spice": "/secure/pdk/cdl/my65_sc.sp",
  "model_lines": [".lib \"/secure/pdk/models/ngspice/models.lib\" tt"],
  "vdd": 1.2,
  "temp_c": 25.0
}
```

```bash
python scripts/calibrate_pdk.py my65.json      # ~2,600 ngspice runs; minutes on a laptop
```

This writes `glitchscope/data/<Liberty library name>/m2_model.json` and
`liberty_vs_spice_energy.csv`. From then on, every analysis using that Liberty library picks
up the calibration automatically.

What the calibration does:

* Supply pins are recognised by name: VDD, VPWR, VPB, VNW and VCC go to the supply; VSS,
  VGND, VNB, VPW, GND and VEE go to ground.
* Each sensitised arc of INV, BUF, NAND2, NOR2, AND2, OR2, XOR2 and XNOR2 (found by
  function) is driven with single pulses over a range of widths, slews and loads.
* That range is scaled to your library's FO4 slew and inverter input capacitance.

Model formats:

* **Vendor models in HSPICE/Spectre-compatible BSIM4 form:** ngspice usually reads them in its
  HSPICE compatibility mode (`set ngbehavior=hsa`, already set).
* **Verilog-A compact models** (PSP, BSIM-CMG, …): compile them with
  [OpenVAF-Reloaded](https://github.com/OpenVAF/OpenVAF-Reloaded) and list the `.osdi` files in
  `GS_OSDI` (colon-separated).

## 3. What not to expect

* GlitchScope does not replace your sign-off power tool.
* It explains where glitch energy comes from and what fixing it is worth.
* Absolute energy inherits the accuracy of your Liberty internal-power tables. The SPICE
  calibration reports the Liberty/SPICE ratio for the calibrated cells, so you can see this
  directly.
