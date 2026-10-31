# Gate drive has a cost

A reproducible SKY130 LDO sizing laboratory

Author and travel representative: Christian Reivan  
GitHub: https://github.com/christianreivan

This educational Code a Chip entry connects pass transistor current capacity,
available gate swing, transconductance sizing closure, and actual terminal loading.
Its main result is directly reproducible from saved native ngspice data: at 100 mV
across the PFET, reducing VSG from 1.8 V to 1.2 V increases the first width estimate
for 50 mA from about 3.05 mm to 10.97 mm.

Open `sky130_ldo_design_lab.ipynb` and run all cells. This verifies the frozen data
and regenerates the calculations and figures without needing the PDK or a lab server.
The submitted notebook contains executed outputs.

## Local notebook setup

Use Python 3.11 or later in an isolated environment.
On Windows, keep the environment folder path short. If pip reports a path length
error while installing JupyterLab, create the environment in a shorter directory.

```text
python -m pip install -r requirements.txt
python -m jupyterlab
```

Open the notebook from this project directory. To check saved evidence directly:

```text
python scripts/device_lab.py check
```

## Native regeneration

The original experiments use ngspice 41 and the public open_pdks.sky130a package
1.0.471_0_g97d0844 with build 20240223_100318. See FOUNDATIONAL_EVIDENCE.json for
the package URL and top model library hash. No PDK is redistributed here.

Install native ngspice and SKY130. Set SKY130_MODEL to the absolute path of
sky130.lib.spice, or set PDK_ROOT to the directory containing sky130A. Set NGSPICE
to the native executable if it is not on PATH. Then run:

```text
python scripts/device_lab.py regenerate --output work/device_run
```

The runner launches real ngspice, records its version and the model hash, and saves
fresh raw tables and logs in a new directory. It refuses a nonempty destination.
Changing the simulator or PDK revision may change the numerical values.
The submitted notebook defaults to saved evidence mode. It does not claim a new
native run merely because Run All successfully redraws the figures.

## Contents

1. sky130_ldo_design_lab.ipynb contains the lesson and executed calculations.
2. scripts/device_lab.py provides portable analysis and optional native regeneration.
3. data/device contains native tables, logs, portable SPICE decks, and declared settings.
4. FOUNDATIONAL_EVIDENCE.json records source hashes, public hashes, and transformations.
5. figures contains connected fixture drawings and their attribution.
6. VERIFICATION.json records notebook execution and evidence checks.

## Evidence boundaries

The evidence is nominal SKY130 compact model simulation at TT and 27 degrees C.
The current capacity results describe isolated pass devices. They do not establish
regulated dropout, closed loop PSR, stability, transient performance, or silicon results.
The continuous sizing root needs legal layout geometry selection and rechecking.
The terminal capacitance fixtures use VDS magnitude 0.9 V, which differs from the
100 mV dropout example. Recharacterize capacitance at the actual connected bias.

## Attribution and license

This submission curates the author's native SKY130 characterization data and uses
original portable scripts. Boris Murmann's Chipathon 2024 examples informed the
device lookup teaching approach. SKY130 and ngspice remain separately licensed
dependencies. Circuit symbols use cirfig_gen under its included MIT notice.
Original notebook content and code use Apache License 2.0.

AI assistance was used for preparation, code adaptation, and checking. Circuit data
are identified native ngspice outputs. All physical claims are limited to that evidence.
