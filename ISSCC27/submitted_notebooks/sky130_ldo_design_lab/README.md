# A complete 50 mA SKY130 LDO with a local gate feedback loop

**Author and travel representative: Christian Reivan**
**Affiliation: Samsung Electronics**
**GitHub: [christianreivan](https://github.com/christianreivan)**

This Code a Chip notebook implements a complete transistor LDO. The circuit
contains a current mirror error amplifier, physical bias generator, PMOS super
source follower gate driver, NMOS pass array, direct output feedback,
compensation, and an output bleeder. The external reference is shared by the
amplifier and bias circuit.

The nominal circuit regulates VIN = 1.2 V to VOUT = 1.0 V for loads from 0 to 50 mA.
The amplifier and driver require a separate VAA = 1.8 V rail. The output capacitor
sweep covers 10, 50, 100, and 350 pF. Every regulator control device uses a public
SKY130 transistor model. There is no behavioral amplifier or controller in the core.

Open [the notebook](sky130_ldo_design_lab.ipynb) for the transistor schematics,
hand derivation, native results, and executable plots. The contribution is a
reproducible connected circuit study of the tradeoffs among gate drive, supply
rejection, light load damping, and transient response.

## Read and run

Use Python 3.11 or later. From this directory, install the requirements and start
JupyterLab:

```text
python -m pip install -r requirements.txt
python -m jupyterlab
```

Open `sky130_ldo_design_lab.ipynb` and select Run All. The included ngspice results
allow every figure and table to be reproduced without installing a simulator.
The notebook contains executed outputs for immediate reading.

## Simulate the complete circuit

Install [ngspice](https://ngspice.sourceforge.io/download.html).
The full circuit runs use ngspice 47. The project includes the required public
SKY130 MOS models and their source manifest, so a separate PDK installation
is not required.

If the executable is named `ngspice` and is on the system search path, no additional
configuration is needed. Otherwise set the `NGSPICE` environment variable to its
absolute path. For example, on Windows PowerShell:

```powershell
$env:NGSPICE = 'C:/Spice64/bin/ngspice_con.exe'
```

Set `RUN_NATIVE = True` in the notebook to generate new transistor simulations and
plot their results. Alternatively, run the complete experiment from the terminal:

```text
python scripts/ldo_lab.py regenerate --all-cases --output work/full_run
```

Choose a new output directory for each run. The runner records the simulator
version, checks the public model files, writes the SPICE decks, runs ngspice,
and saves the new native tables and logs. The analysis functions accept that
directory directly. Numerical results can differ with simulator versions.

The canonical circuit is in [circuits/ldo.spice](circuits/ldo.spice).
Its [circuit description](circuits/ldo.json) records every transistor terminal,
dimension, resistor, and capacitor. Simulation fixtures also include the supply,
reference, and load sources and the requested analysis commands.

## What is measured

1. DC regulation and device operating points from 0 to 50 mA.
2. VIN and VAA supply transfer from 1 Hz to 1 GHz.
3. Reference transfer and closed loop output impedance.
4. Precision loop voltage injection, its port impedance condition, and small load steps.
5. Output capacitor endpoints at 0 and 50 mA.
6. Five process corners at 0, 27, and 85 °C with 100 pF.
7. Large load steps, startup, DC input sweeps, and intrinsic output noise.
8. The effect of removing the VIN coupling capacitor from the same connected circuit.

At nominal full load and 100 pF, the worst VIN transfer is about −18.5 dB.
A 0 to 50 mA step with 10 ns edges produces approximately 363 mV undershoot.
The auxiliary rail is evaluated separately and has a weak rejection corner.
The notebook explains these limitations alongside the corresponding results.

## Physical implementation assumptions

The source tied body of the NMOS pass array requires suitable well isolation.
The 1.8 V auxiliary supply provides gate drive headroom and contributes power.
The reference and supply generators are ideal in the declared tests, except for
the explicit ripple excitation. The noise analysis includes transistor and
resistor noise but excludes external generator noise.

These are compact circuit simulations.

## Files

1. `sky130_ldo_design_lab.ipynb` contains the complete lesson and executed results.
2. `circuits` contains the canonical complete circuit.
3. `scripts/ldo_lab.py` runs and analyzes the complete regulator experiments.
4. `data/ldo` contains native simulation tables, portable decks, and conditions.
5. `models` contains the public model archive, original license, and source hashes.
6. `figures` contains the transistor schematics and editable drawing descriptions.
7. `data/device` and `scripts/device_lab.py` provide supporting device characterization.

## Attribution and license

Original notebook content and scripts use Apache License 2.0. SKY130 model files
retain the original Apache License 2.0 and copyright notices.
Circuit symbols use cirfig_gen under the included MIT notice. Professor Boris Murmann's
Chipathon teaching examples informed the supporting transistor characterization
workflow.
