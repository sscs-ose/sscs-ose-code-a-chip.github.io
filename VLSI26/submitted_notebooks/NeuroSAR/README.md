# NeuroSAR: PINN-Based Metastability-Aware SAR ADC Waveform Engine in Sky130

[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)]()
[![PyTorch](https://img.shields.io/badge/framework-PyTorch%202.0%2B-orange)]()
[![PDK](https://img.shields.io/badge/PDK-SkyWater%20Sky130-green)]()
[![Tests](https://img.shields.io/badge/tests-46%20passed-brightgreen)]()

**Author:** Ayan Biswas, Purdue University — [ayanb@purdue.edu](mailto:ayanb@purdue.edu)

**Submission:** IEEE SSCS Code-a-Chip / VLSI 2026

---

## What Is NeuroSAR?

NeuroSAR is a physics-informed neural network (PINN) surrogate that models the complete transient behaviour of a charge-redistribution SAR ADC — DAC settling, comparator regeneration, metastability, and energy — in real time. It is designed as an educational, interactive, and technically rigorous open-source tool for mixed-signal circuit designers and students.

Instead of spending minutes per SPICE simulation to explore one design point, NeuroSAR lets you move sliders in a Jupyter notebook and see the full SAR ADC conversion waveform update instantly.

The key difference from a black-box ML regression is that NeuroSAR embeds actual circuit equations into the training loss:

| Physics Residual | Equation | What It Enforces |
|---|---|---|
| KCL at DAC node | `(C_total + C_load) · dVdac/dt ≈ 0` | Current conservation during settling |
| Charge conservation | `ΔV = C_k / C_denom · Vref · (2·bit_k − 1)` | Correct voltage steps at each switching event |
| Comparator ODE | `dVcomp/dt = (gm / CL) · Vcomp` | Cross-coupled latch regeneration dynamics |
| Smoothness | `‖d²v/dt²‖²` penalty | Suppresses non-physical oscillations |

The result is a differentiable surrogate that is physically consistent, not just statistically fit.

---

## For Judges: How to Run This Project

Everything below is designed to work out of the box on a standard machine with Python 3.9+. No proprietary tools, no paid licenses, no GPUs required.

### Step 0 — Clone and Set Up Environment

```bash
git clone https://github.com/<your-org>/NeuroSAR.git
cd NeuroSAR
```

Create an isolated virtual environment (strongly recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

Install all dependencies:

```bash
pip3 install -r requirements.txt
```

This installs PyTorch, NumPy, Pandas, Plotly, ipywidgets, Jupyter, pytest, and everything else needed. The full list is in `requirements.txt`.

### Step 1 — Run the Automated Demo (Fastest Path)

This single command generates data, trains a model, evaluates it, and produces figures:

```bash
python scripts/run_demo.py --epochs 100 --samples 4000
```

Expected output:
- Dataset saved to `data/processed/sar_dataset.pt`
- Best model checkpoint saved to `data/checkpoints/best_model.pt`
- Evaluation metrics printed to console
- Figures saved to `assets/figures/`

Total time: ~2-5 minutes on a laptop CPU.

### Step 2 — Run the Tests

```bash
pytest tests/ -v
```

All 46 tests should pass. They verify tensor shapes, physics residual correctness, dataset generation, and inference flow.

### Step 3 — Walk Through the Notebooks

```bash
jupyter notebook notebooks/
```

> **Note:** If `jupyter lab` throws an error about missing `attrs`, use `jupyter notebook` instead, or install the missing package with `pip install attrs`.

Open the notebooks in this order:

| Order | Notebook | What It Shows |
|---|---|---|
| 1 | `00_Project_Overview.ipynb` | SAR ADC physics background, PINN theory, project architecture (all markdown, no code to run) |
| 2 | `01_Generate_Dataset.ipynb` | Generates 8,000 synthetic SAR waveforms, visualizes DAC settling and comparator regeneration |
| 3 | `02_Train_PINN.ipynb` | Trains the PINN for 50+ epochs, plots loss curves decomposed by physics term |
| 4 | `03_Evaluate_Waveforms.ipynb` | Loads the trained model, computes MSE/MAE/R² metrics, overlays predicted vs ground truth |
| 5 | `04_FoM_Explorer.ipynb` | Sweeps Cu vs gm, generates heatmaps for energy, metastability, ENOB, and Walden FoM |
| 6 | `05_Inverse_Design.ipynb` | Runs gradient-based optimization through the PINN to minimize metastability under an energy budget |
| 7 | `06_NeuroSAR_Interactive_Demo.ipynb` | **Flagship demo** — live sliders, animated conversions, metastability visualization |

Each notebook includes `sys.path.insert(0, '..')` at the top so imports resolve correctly when run from the `notebooks/` directory.

### Step 4 (Optional) — Train With More Data / Epochs

For a more thoroughly trained model:

```bash
bash scripts/train.sh 500
```

This generates 8,000 samples and trains for 500 epochs (~10-20 minutes on CPU, ~2-3 minutes on GPU).

---

## Why This Matters

### The Problem with SPICE Alone

- A single 10-bit SAR ADC transient simulation takes seconds to minutes. Sweeping a 9-dimensional design space is computationally intractable.
- SPICE is non-differentiable. You cannot back-propagate through it to perform inverse design or sensitivity analysis.
- SPICE gives waveforms but no analytical insight into why a capacitor mismatch degrades ENOB or how close a comparator is to metastability.
- Interactive, slider-driven exploration is impossible at SPICE speeds.

### What PINNs Add

1. **Speed** — Full conversion waveform in under 1 ms (vs. seconds for SPICE).
2. **Physical consistency** — Not a black-box fit. The model is constrained by KCL, charge conservation, and the comparator ODE.
3. **Differentiability** — Enables gradient-based inverse design: "given a target ENOB and energy budget, find the optimal Cu and gm."
4. **Interactivity** — Real-time Jupyter widget exploration with instant feedback.

---

## Model Architecture

```
Input: [Vin, Vref, Cu, Cload, gm, τ_regen, Vos, T, fs]  (9 design params)
       + bit_index (which trial)
       + Fourier features of time axis

         │
         ▼
  ┌────────────────────────────┐
  │  Fourier Feature Encoder   │  sin/cos of (B·t), B ~ N(0, σ²)
  └──────────┬─────────────────┘
             │
  ┌──────────▼──────────┐
  │  Shared MLP Trunk   │  256 → 256 → 256 → 128  (tanh activations)
  └──────────┬──────────┘
             │
  ┌──────────┼──────────┬──────────┐
  ▼          ▼          ▼          ▼
V_dac(t)  V_diff(t)  V_comp(t)  Energy
 (1-D)     (64-D)     (64-D)    (1-D)
```

Total parameters: ~250K. Activation: tanh (preserves smooth second derivatives needed for physics residuals).

Training loss:
```
L = w_data · L_data  +  w_kcl · L_kcl  +  w_charge · L_charge  +  w_ode · L_comp_ode  +  w_smooth · L_smooth
```

All residuals are computed via PyTorch autograd, making constraint enforcement exact.

---

## Design Space

The PINN accepts these design parameters as inputs:

| Parameter | Symbol | Range | Unit |
|---|---|---|---|
| Input voltage | V_in | 0 – 1.8 | V |
| Reference voltage | V_ref | 1.8 | V |
| Unit capacitor | C_u | 1 – 50 | fF |
| Load capacitance | C_load | 10 – 500 | fF |
| Comparator transconductance | g_m | 50 µ – 2 m | S |
| Regeneration time constant | τ_regen | 10 – 500 | ps |
| Comparator offset | V_os | -10 – +10 | mV |
| Temperature | T | 250 – 400 | K |
| Sample rate | f_s | 1 – 200 | MHz |

Resolution: 10 bits. Time resolution: 64 points per bit cycle.

---

## Repository Layout

```
NeuroSAR/
├── README.md                           ← You are here
├── LICENSE                             ← Apache 2.0
├── requirements.txt                    ← Python dependencies
├── pyproject.toml                      ← Package metadata
├── setup.cfg                           ← Setup configuration
├── Makefile                            ← Build/test/train shortcuts
├── .gitignore
│
├── src/                                ← Core Python modules
│   ├── __init__.py
│   ├── config.py                       ← Design space bounds, training hyperparams
│   ├── utils.py                        ← Seeding, normalization, device selection
│   ├── physics.py                      ← DAC model, comparator ODE, metastability, energy
│   ├── dataset.py                      ← Synthetic generator (Mode A) + SPICE parser (Mode B)
│   ├── simulate_spice.py               ← ngspice deck generator for Sky130
│   ├── pinn_model.py                   ← Multi-head PINN with Fourier features
│   ├── losses.py                       ← 4 physics residuals + data loss
│   ├── train_pinn.py                   ← Training pipeline with checkpointing
│   ├── evaluate.py                     ← Metrics, single-point inference, CSV export
│   ├── fom_analysis.py                 ← 1D/2D parameter sweeps, FoM surfaces
│   ├── inverse_design.py               ← Differentiable optimization through surrogate
│   ├── plotting.py                     ← Plotly waveforms, heatmaps, training curves
│   ├── animation.py                    ← Animated bit-cycle and metastability plots
│   ├── interactive_ui.py               ← ipywidgets dashboard with live sliders
│   └── export_results.py               ← Submission packaging utilities
│
├── notebooks/                          ← 7 Jupyter notebooks (main deliverable)
│   ├── 00_Project_Overview.ipynb
│   ├── 01_Generate_Dataset.ipynb
│   ├── 02_Train_PINN.ipynb
│   ├── 03_Evaluate_Waveforms.ipynb
│   ├── 04_FoM_Explorer.ipynb
│   ├── 05_Inverse_Design.ipynb
│   └── 06_NeuroSAR_Interactive_Demo.ipynb
│
├── scripts/                            ← CLI entry points
│   ├── run_demo.py                     ← One-command full demo
│   ├── train.sh                        ← Training launcher
│   ├── evaluate.sh                     ← Evaluation launcher
│   └── package_submission.sh           ← Collect submission artefacts
│
├── tests/                              ← 46 unit tests
│   ├── test_shapes.py                  ← Tensor shape consistency
│   ├── test_losses.py                  ← Physics residual correctness
│   ├── test_dataset.py                 ← Dataset generation validation
│   └── test_inference.py               ← End-to-end inference flow
│
├── data/                               ← Data directories (auto-populated)
│   ├── raw/
│   ├── processed/                      ← Generated .pt dataset files
│   ├── spice/                          ← ngspice deck outputs
│   ├── checkpoints/                    ← Model checkpoints
│   └── exports/                        ← CSV/JSON exports
│
├── assets/                             ← Visual artefacts
│   ├── figures/
│   ├── gifs/
│   └── slides/
│
└── docs/                               ← Technical documentation
    ├── overview.md                     ← High-level project overview
    ├── physics_model.md                ← Physics residual derivations
    ├── training_plan.md                ← Feature engineering, loss balancing
    ├── submission_checklist.md         ← IEEE SSCS pre-submission checklist
    ├── video_script.md                 ← 3-minute video script
    └── TECH_REP.md                     ← Full technical report
```

---

## Expected Outputs

After running `python scripts/run_demo.py`, you will see:

**Console output:**
```
[NeuroSAR] Dataset saved → data/processed/sar_dataset.pt  (4000 samples)
[NeuroSAR] Model parameters: 249,858
[NeuroSAR] Training for 100 epochs on cpu ...
  Epoch    1/100 | train 9.20e+15 | val 5.85e+14 | ...
  Epoch  100/100 | train 2.31e-02 | val 3.44e-02 | ...
[NeuroSAR] Best checkpoint → data/checkpoints/best_model.pt
[NeuroSAR] Evaluation metrics:
  mse_vdac       : ...
  mse_vcomp      : ...
  r2_vcomp       : ...
```

**Generated figures** in `assets/figures/`:
- `demo_dac_waveform.png` — DAC trial voltage staircase
- `demo_comparator_regen.png` — Comparator regeneration curves per bit
- `demo_conversion_summary.png` — Three-panel plot (DAC + settling + regen)
- `demo_energy_heatmap.png` — Energy vs Cu and gm

**Interactive notebook** (`06_NeuroSAR_Interactive_Demo.ipynb`):
- Sliders for Vin, Cu, Cload, gm, τ, Vos, temperature, sample rate
- Live-updating waveform plots
- Real-time FoM metrics (energy, metastability, ENOB, Walden FoM)
- Animated conversion cycle and metastability comparison

---

## Replacing Synthetic Data with Real Sky130 SPICE Waveforms

The default demo uses an analytical physics-based waveform generator (`src/dataset.py`, Mode A). To train on real transistor-level data:

### 1. Install ngspice and the Sky130 PDK

```bash
# ngspice
sudo apt-get install ngspice       # Ubuntu/Debian
brew install ngspice                # macOS

# Sky130 PDK (via volare or open_pdks)
pip install volare
volare enable --pdk sky130 --version 0.0.34
export PDK_ROOT=$HOME/.volare
```

### 2. Generate a SPICE deck

```python
from src.simulate_spice import generate_ngspice_deck

deck_path = generate_ngspice_deck(
    vin=0.9, vref=1.8, cu_fF=10.0, n_bits=10,
    sim_time_ns=100.0, corner="tt", temp_c=27.0,
)
# Edit the generated .spice file to uncomment the .lib line
# and set $PDK_ROOT to your Sky130 installation
```

### 3. Run ngspice and parse the output

```bash
ngspice -b data/spice/sar_adc_tt.spice
```

```python
from src.simulate_spice import parse_ngspice_output
waveforms = parse_ngspice_output("data/spice/tran_output.csv")
```

### 4. Load into the training pipeline

```python
from src.dataset import load_spice_csv, build_dataloaders
data = load_spice_csv("data/spice/tran_output.csv")
train_dl, val_dl, stats = build_dataloaders(data)
# The rest of the training pipeline is identical
```

The PINN architecture and loss functions are agnostic to the data source — switching from synthetic to SPICE data requires no code changes to the model or training loop.

---

## Makefile Shortcuts

```bash
make install          # pip install -e ".[dev]"
make test             # pytest tests/ -v
make train            # Generate data + train 500 epochs
make evaluate         # Evaluate best checkpoint
make demo             # Run full demo script
make clean            # Remove generated artefacts
make package          # Run tests + collect submission artefacts
make lint             # Compile-check all source files
```

---

## Key Technical Details

For deeper understanding, see the `docs/` folder:

- **[docs/physics_model.md](docs/physics_model.md)** — Full derivations of each physics residual with equations
- **[docs/training_plan.md](docs/training_plan.md)** — Feature engineering, loss weight strategy, evaluation metrics
- **[docs/TECH_REP.md](docs/TECH_REP.md)** — Complete technical report with results and references
- **[docs/video_script.md](docs/video_script.md)** — Scene-by-scene script for a 3-minute submission video
- **[docs/submission_checklist.md](docs/submission_checklist.md)** — Pre-submission quality checklist

---

## Citation

If you use NeuroSAR in your research or course materials, please cite:

```bibtex
@misc{biswas2025neurosar,
  title        = {{NeuroSAR}: {PINN}-Based Metastability-Aware {SAR} {ADC}
                  Waveform Engine in {Sky130}},
  author       = {Biswas, Ayan},
  year         = {2025},
  howpublished = {\url{https://github.com/<your-org>/NeuroSAR}},
  note         = {IEEE SSCS Code-a-Chip Submission, Purdue University}
}
```

---

## License

Copyright 2025 Ayan Biswas, Purdue University

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

---

*Developed by Ayan Biswas at Purdue University. Submitted to the IEEE Solid-State Circuits Society (SSCS) Code-a-Chip Travel Grant program. Contributions, issues, and pull requests are welcome.*
