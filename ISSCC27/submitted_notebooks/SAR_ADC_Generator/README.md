# SARGen - automated, explainable SAR ADC generator (SKY130)

IEEE SSCS Code-a-Chip, ISSCC 2027 submission. The notebook is `SAR_ADC_Generator.ipynb`.

**Author:** Rajinthan Rameshkumar, Dept. of Electronic and Telecommunication Engineering,
University of Moratuwa, Sri Lanka (rajinthan519@gmail.com, [rajinthan.com](https://rajinthan.com))

Enter a resolution (4-8 bit) and a sample rate; the flow characterizes the SKY130 PDK, sizes the
SAR ADC, generates a transistor-level netlist, simulates it with ngspice and reports ENOB, INL/DNL,
histogram, FFT, comparator offset, power and Monte-Carlo yield, together with an animated explanation
of the conversion. The same code then generates the layout from the PDK's own cells, signs it off and
re-simulates the extraction.

**Results** (extracted layout, 10 MS/s, 1.8 V, typical corner; numbers from `results/`):

| resolution | core area | ENOB, schematic -> layout | max DNL / INL | power |
|---|---|---|---|---|
| 4 bit | 2762 µm² | 3.97 -> 3.96 | 0.07 / 0.08 LSB | 26 µW |
| 6 bit | 5382 µm² | 5.91 -> 5.98 | 0.11 / 0.11 LSB | 65 µW |
| 8 bit | 15854 µm² | 7.68 -> 7.71 (7.88 at -0.5 dBFS) | 0.25 / 0.22 LSB | 289 µW |

Every block and core: DRC 0 (KLayout and Magic), LVS match (Netgen), antenna check; no missing codes.

## Quick start

All tools come from the [IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS) container (tag `2026.10`).

```bash
# headless, from this folder inside the container
python3 run_flow.py --bits 4            # results in build/4bit/
python3 run_flow.py --bits 6 --fs 5e6   # any resolution 4..8

# robustness of the nominal design (needs build/4bit from run_flow.py)
python3 run_sweep.py all --bits 4       # PVT, input frequency, sample rate, comparator delay
python3 run_sweep.py mc --bits 4        # transistor-level mismatch runs vs behavioral model
python3 collect_results.py              # copy small result files to results/ (shown in the notebook)

# or open the notebook
jupyter lab SAR_ADC_Generator.ipynb
```

### Layout (same container, gLayout environment from `layout/setup_env.sh`)

```bash
bash layout/setup_env.sh                     # once: pinned gLayout venv (gdsfactory 7.7)
unset PYTHONPATH; . /foss/designs/.venvs/sargen-glayout/bin/activate
export PDK=sky130A PDK_ROOT=/foss/pdks PYTHONPATH=$PWD
for b in unitcell cdacu comparator topsw sarlogic; do python run_layout.py $b --bits 4; done
python run_layout.py cdacu --bits 4 --pex; python run_layout.py comparator --bits 4 --pex
python run_layout.py core --bits 4 --pex     # routed core: DRC (KLayout + capm.10, Magic), LVS (Netgen), PEX
python collect_layout.py 4                   # signoff table + images -> results/4bit/layout/
python run_postlayout.py --bits 4            # same testbench with the extracted blocks / full extracted core
```

Each block is closed at DRC 0 / LVS match before the next is built; `--bits 6` runs the same generators.

**Google Colab:** the first code cell of the notebook installs ngspice (conda-forge) and the SKY130 PDK
(`ciel`, pinned version) in a few minutes; *Run all* takes about 10 minutes on 2 cores (tested on a clean
Ubuntu 22.04 image with Colab's package versions).

## Flow

| stage | module | what it does |
|---|---|---|
| spec | `sargen/spec.py` | N, fs, Vref, corner, LSB-based targets (DNL, offset, noise, settling) |
| characterize | `sargen/characterize.py` | ngspice: A_VT (nfet/pfet), TG and driver R_on x W, MIM density; MIM matching from the PDK model |
| size | `sargen/sizing.py` | unit cap (matching vs kT/C vs min size), StrongARM (offset, preamp decision), switches and drivers (settling); every decision logged |
| netlist | `sargen/netlist.py` | MIM unit-cap CDAC, transmission gates, binary-scaled drivers, StrongARM, SAR logic from `sky130_fd_sc_hd` cells (XSPICE option), break-before-make timing |
| simulate | `sargen/spice.py`, `sargen/flow.py` | single conversion, comparator offset MC, ramp (histogram), coherent sine (FFT); chunks run in parallel |
| measure | `sargen/metrics.py` | DNL/INL (code density and transition levels), SNDR/SFDR/THD/ENOB, Walden FoM |
| explain | `sargen/model.py`, `sargen/anim.py` | behavioral model (PDK-calibrated MC) and animated binary search |
| verify | `sargen/sweep.py` | PVT, input-frequency and sample-rate sweeps of a fixed design, comparator delay, SPICE vs behavioral MC |
| layout | `sargen/layout/` | PDK PCells placed and routed by code: CDAC unit cell + common-centroid array with dummy ring (`unitcell.py`), StrongARM (`strongarm.py`), top-plate switch (`topswitch.py`), SAR logic via LibreLane (`sarlogic.py`), routed core (`core.py`) |
| signoff | `sargen/layout/verify.py` | KLayout DRC + capm.10 deck, Magic DRC, Netgen LVS, Magic PEX, PNG render |

## Architecture (current)

Single-ended, binary-weighted charge-redistribution CDAC with bottom-plate sampling; the MSB is set at the
end of sampling and the other plates are grounded slightly later (break-before-make), so the top plate stays
inside the supply rails; StrongARM comparator against Vcm = Vref/2; synchronous SAR logic from standard cells.
Input range 0..Vref.

Idealizations (stated in the notebook's limitations): clock-phase generation, Vref and Vcm are ideal sources;
comparator noise is the input pair's thermal noise injected as an equivalent source (no transient device noise in
ngspice); post-layout runs use capacitance-only extraction, with wiring resistance checked separately (Magic
extresist).

## Roadmap

- [x] 4-bit pre-layout flow: characterization, sizing, netlist, ramp/FFT/MC metrics, animation and an interactive explorer
- [x] layout generators from SKY130 PDK PCells: CDAC unit cell with its own switches, 3-8 bit common-centroid
      CDAC arrays, compact StrongARM comparator (findings: [docs/layout_findings.md](docs/layout_findings.md))
- [x] DRC/LVS (KLayout incl. capm.10, Magic, Netgen) and PEX, post-layout re-simulation
- [x] top-plate switch, SAR logic (LibreLane), routed 4-, 6- and 8-bit cores, DRC 0 / LVS match; full-core
      post-layout simulation (4 bit: ENOB 3.96, DNL 0.07 LSB)
- [x] top-plate switch sizing that holds at hot and cold corners (leakage-aware rule, `studies/top_switch_trials.py`)
- [x] antenna check of the routed cores, antenna diodes on the CDAC control trunks
- [x] matching rework: dummies at both ends of every latch device and the top-plate switch, latch halves next to the
      axis, diffusion-length stress from the layout into the netlist (`sargen/layout/lod.py`, `studies/lod_*.py`)
- [ ] charge-balanced top-plate switch (the 8-bit core has a 1.4-LSB offset; ENOB 7.88 at -0.5 dBFS, 7.71 at full scale)
- [ ] TinyTapeout tile integration (pins, analog ground, Vref decoupling)
- [x] 4..8-bit scaling (ENOB / power / capacitance / FoM trends)
- [x] robustness: PVT, input frequency, sample rate, comparator delay, transistor-level mismatch runs
- [x] Colab install path

## Use of AI tools

SARGen's code, simulation scripts and documentation were written with the help of an AI coding assistant (Claude by
Anthropic, used through Claude Code). The author set the specification and the design rules, directed and reviewed the
work, and checked the results; every reported number comes from the simulations, signoff runs and result files in this
folder.

## License

Apache-2.0 (see `LICENSE`).
