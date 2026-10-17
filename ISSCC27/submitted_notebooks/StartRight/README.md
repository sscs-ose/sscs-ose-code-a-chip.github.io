# StartRight

**Author: Adnane Essoufi. Solo project.**

StartRight checks startup states in declared SKY130 bias-circuit examples. It connects a DC return curve to operating points in the intact circuit, then tests whether a useful current output reaches its declared startup requirement. It also rejects DC data that fails the gate-cut audit.

The example shows how a numerical minimum conductance can conceal an unwanted state. A conventional startup device corrects the demonstrated failure. A matched sizing study then shows why the larger device is not always the better energy choice.

The circuit family and startup topology are established work. The contribution is the open verification workflow and its measured example. The shared verifier supports the main inverse-Widlar example, a conventional beta multiplier and a resistor-biased NMOS mirror. These are bounded schematic examples, not a general proof of startup reliability or a new transistor topology.

## Start here

Open StartRight.ipynb for the explanation and live examples. The circuit drawing and the generated netlists show the connections. The notebook clearly separates live execution from saved studies.

For a command-line run:

```powershell
python startright.py --startup-width none
python startright.py --startup-width .42
python startright.py --circuit beta_multiplier
python startright.py --circuit resistor_biased_mirror
```

Each run verifies model checksums, audits both DC sweep directions, checks candidate points in the intact circuit and runs a loaded cold start. Each invocation gets a separate run directory under results/verification/, with its raw cases under results/pilot/. This prevents concurrent invocations from overwriting each other. A completed analysis can still report fails_declared_bench. Read startup_verdict rather than treating a zero process exit as a circuit pass. A report can retain a late band-entry time and diagnostic source work when the deadline is missed. That run still fails and is excluded from energy rankings.

## Tested setup

The verified environments are Windows and an Alpine Linux VM on the same computer, both with Python 3.12 and ngspice 47. Windows uses the official portable binary and 7-Zip. Linux uses a binary compiled from pinned source. The initial Windows setup downloaded models/tools again; the Linux setup verifies the same model files and source archive. This is cross-OS and cross-build evidence, not a second simulator or an independent machine.

From this project directory, with 7-Zip installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock-windows-py312.txt
.\.venv\Scripts\python.exe bootstrap.py
.\.venv\Scripts\python.exe reproduce_short.py
```

For notebook execution, install the complete tested notebook dependency lock in the same environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebook-lock-windows-py312.txt
.\.venv\Scripts\python.exe execute_notebook.py
```

The current notebook passed all eight code cells in actual Jupyter kernels on both tested platforms. execute_notebook.py launches a new kernel with the selected Python executable, validates the notebook format and records source hashes. It preserves live simulation and saved-study labels. Use this environment as the kernel when opening the notebook interactively. bootstrap.py downloads only the required model/license subset from a pinned upstream commit and the official portable ngspice 47 archive. It verifies SHA-256 checksums and writes local configuration. It does not install system software. Rerunning it reuses files whose checksums match.

### Linux setup

With Python 3.12, `gcc`, `g++` and `make` installed, run from this project folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-notebook-lock-linux-py312.txt
.venv/bin/python bootstrap_linux.py --jobs 2
.venv/bin/python reproduce_short.py
.venv/bin/python portability_check.py
.venv/bin/python execute_notebook.py
```

The source build uses a SHA-256-pinned official ngspice 47 archive, enables KLU/OpenMP and disables the GUI/readline/FFTW dependencies. Its compiler, flags, binary checksum and logs are retained. It installs inside `.cache/`, with no system installation. An existing ngspice 47 executable can instead be configured with `bootstrap.py`.

The tested Linux environment is Alpine 3.21 with Python 3.12 in a workspace-local QEMU/WHPX guest on the Windows computer. Its full Python lock is separate from the Windows lock. The five nominal verifier cases and two matched refined sizing cases were freshly simulated. Compare the saved records with `python compare_platforms.py`; that command does not rerun SPICE. Colab and macOS remain unverified. `requirements.txt` contains the top-level simulation dependencies.


## Main results

At TT, 27 °C and VDD = 1.8 V, the unassisted circuit has three confirmed bias points near 0.0177 V, 0.1182 V and 1.1601 V with GMIN = 1 fS. With the default GMIN of 1 pS, the same scan finds only the high point. Other numerical settings are held fixed in that comparison. A default-GMIN startup can eventually reach the high state, so a loose startup observation would miss the lower-GMIN failure.

The useful output is about 0.773 µA over the tested 10 kΩ to 1 MΩ load range. Both startup widths, 0.42 and 1 µm at L=1 µm, meet the nominal requirement in all six load/ramp combinations. The six unassisted controls fail it.

With the 1 µs ramp and 100 kΩ load, refined readiness times are about 18.14 and 16.36 µs for the smaller and larger startup devices. With the 1 ms ramp, net source work to the same readiness point is about 7.86 and 8.38 nJ. The larger device uses about 6.7% more energy in that case. This compares two working circuits against the same requirements. The failed controls in this matched sizing study never reach the valid band, so no energy-to-readiness value is assigned.

The loaded qualification covers five corners at -20, 27 and 85 °C. Both assisted sizes pass all 15 tested conditions. Each condition uses its intended high-state current as the target, computed before the cold start. This is not a claim of constant current across PVT. Both sizes also pass the 12 supply-recovery cases and four additional unchanged-design cases recorded in results/loaded/.

## Reuse checks

The conventional beta multiplier uses a 4:1 NMOS width ratio, equal 2 µm lengths and an ideal 100 kΩ source resistor. The PMOS mirror uses W/L=4/2 µm. The reference and output NMOS devices use 2/2 µm; the source-degenerated NMOS uses 8/2 µm. Only the source-degenerated NMOS gate is cut, preserving the reference diode connection.

The healthy control is an acyclic resistor-biased NMOS mirror. A 1 MΩ resistor drives a 2/2 µm diode-connected reference. Its output device also uses 2/2 µm. Cutting only the output gate leaves the reference voltage independent of the scan input. The flat return curve is a positive control, not a feedback stability test.

Both examples use a resistor from VDD to the current output and a 100 fF output capacitor. The beta multiplier has 100 fF at a, b and s; the healthy control has 100 fF at b. Junction geometry follows the main example and NRD/NRS remain at their zero defaults. See results/reuse/additional_circuits.png and circuits.py.

The shared verifier finds one confirmed candidate and a passing cold start in all eight tested combinations for each additional circuit: GMIN of 1 pS/1 fS, 100 kΩ/1 MΩ loads and 1 µs/1 ms ramps, at TT and 27 °C. Each target comes from that circuit's intended loaded operating point. No cross-family energy ranking is claimed. Original inverse-Widlar failure/pass regressions still pass. These extra circuits have not received the main example's PVT or recovery qualification.

Adapters supply the cut and intact netlists, state-node names, an intended-state seed and a minimum intended bias. The verifier is shared. A new adapter needs electrical justification for its gate cut; accepting a Python object alone does not validate a new topology. All declared examples use the selected models' disabled DC gate leakage.

## Saved cross-platform check

The same numerical source files were used on Windows and in the Alpine Linux VM. All five fresh nominal cases agree in candidate count and startup verdict, including the two failing inverse-Widlar controls. The confirmed bias points and intended currents match at the recorded SPICE output precision. The Linux VM runs on the same physical computer, so this is cross-OS and cross-build evidence, not an independent-machine or second-simulator test.

Two additional matched slow-ramp runs check the sizing result. Both startup sizes pass the same current/compliance/deadline/hold contract on Linux. The larger size uses 6.693% more source energy there. The largest energy difference from the fresh Windows reference is 2.847e-06%. The comparison limits were 10 µV for bias points, 0.1% for intended current and 1% for the refined sizing time/energy.

These are saved portability results. `reproduce_short.py` and `portability_check.py` regenerate the simulations on each platform. `compare_platforms.py` compares saved records and does not rerun SPICE. The wider PVT and recovery studies remain Windows results. These differences describe agreement between the recorded runs, not bounds on simulation or physical error.

## Contract and measurements

The nominal loaded target is the intended current at the 100 kΩ operating point, approximately 0.773 µA. The allowed band is 5%, with output voltage at least 0.3 V and VDD at least 1.7 V. The output must reach the band within 1 ms after the supply ramp finishes and remain there through the run's end for at least 2 ms.

Cold-start time begins at simulation t=0. The source stays at zero for 1 µs before ramping. Readiness is interpolated between samples. Net source work integrates VDD times the complete circuit's source current through the readiness event. The output load and declared capacitors are included. Recovery energy is not compared because initial stored energy would also need accounting.

The event measurement was checked against an analytic settling example. Four selected time-step/tolerance refinements changed energy by less than 0.35% and readiness by less than 0.3%. These checks bound the reported example; they are not universal numerical error guarantees.

## Model scope and limitations

The core uses M5 W/L=12/1 µm, M4 W/L=0.42/20 µm and M1/M2/M3 W/L=4/1 µm. The current-output device uses 0.42/20 µm. Each core node and the output have declared 100 fF loads. Rectangular junction areas/perimeters use 0.29 µm diffusion extensions. These are schematic assumptions, not extracted geometry. The supported configuration keeps NRD/NRS at their zero defaults. Intrinsic model resistance is still present.

Small nonzero NRD/NRS trials produced rejected DC data across the tested settings. Larger values produced valid scans. This supports a numerical-conditioning concern but is not a complete diagnosis. The data audit rejects transient operating-point fallback and nonzero cut-gate current before reporting candidates. A successful simulator exit alone is insufficient.

The high state draws about 113 µA including the output branch. This is a verification example, not an optimized batteryless reference. The original limited-source failure hypothesis remains unconfirmed. No mismatch yield, extracted layout or silicon behavior is claimed. Gate leakage is disabled in the selected upstream model. Actual loading and leakage can change the state structure. The crossing finder includes exact sampled zeros and scan endpoints, and rejects sampled zero intervals as ambiguous. Finite scans can still miss close crossings or unsampled tangent roots.

## Regenerate the saved studies

The short live path is reproduce_short.py or the notebook. For the complete saved studies, run these scripts from the project directory:

```powershell
python widlar_confirm.py
python widlar_stability.py
python widlar_cold.py
python widlar_numerical.py
python widlar_conditions.py
python validate_widlar.py
python loaded_startup.py
python refine_loaded.py
python validate_loaded.py
python qualify_loaded.py
python recovery_loaded.py
python heldout_loaded.py
python validate_qualification.py
python plot_widlar.py
python plot_loaded.py
python draw_circuit.py
python qualify_reuse.py
python plot_reuse.py
python draw_reuse.py
python check_algorithms.py
python portability_check.py
python compare_platforms.py
```

Raw decks and logs are regenerated under results/pilot/. Summary JSON and figures are retained separately. The rejected-contact fixture is a negative example for the data audit, not accepted operating-point evidence.

## References and license

- [Wang et al., Performance Verification of Start-Up Circuits in Reference Generators, 2012](https://class.ece.iastate.edu/vlsi2/docs/Papers%20Done/2012-08-MWSCAS-YW.pdf), especially Figs. 1, 2 and 8. We use the circuit family and gate-cut connection with different models and declared dimensions.
- [Wang et al., Practical Methods for Verifying Removal of Trojan Stable Operating Points, 2013](https://class.ece.iastate.edu/vlsi2/docs/Papers%20Done/2013-05-ISCAS-YW.pdf), for verification methods and their limits.
- [Official ngspice 47 source archive](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/), pinned in dependency_manifest.json for the Linux build.
- [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf), for GMIN and operating-point options.
- [Pinned upstream SKY130 model source](https://github.com/google/skywater-pdk-libs-sky130_fd_pr/tree/f62031a1be9aefe902d6d54cddd6f59b57627436).

Project code is Apache-2.0 licensed. Model copyright and licenses remain with the SkyWater PDK Authors. Prior Code-a-Chip submissions informed the presentation and validation standard; their source code was not copied into this project.
