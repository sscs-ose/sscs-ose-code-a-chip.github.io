# Reproducibility Manifest — NeuroSAR

Every claim on the README is traceable to a cell in a notebook that can be re-run on a clean machine. This file lists the exact versions, commands, and expected artefacts.

## 1. System requirements

- Linux (tested Ubuntu 22.04) or macOS. Windows via WSL2.
- Python 3.9 – 3.12.
- 8 GB RAM, 4 CPU cores minimum. GPU not required.
- ~2 GB disk for the PDK + generated data.

## 2. Pinned toolchain versions

| Tool | Pinned version | Notes |
|---|---|---|
| Python | `3.10.12` | Any 3.9+ works; 3.10 is what CI runs |
| PyTorch | `2.2.0` | CPU-only wheel is sufficient |
| ngspice | `46` | Built from source (see below) |
| SKY130 PDK | `google/skywater-pdk` commit `f70d8ca` | `sky130A` variant |
| OpenFASOC (optional, for layout teaser) | commit `91e6a7d` | |

All other Python dependencies are pinned in [`requirements.txt`](requirements.txt).

## 3. One-command reproduction

```bash
make reproduce
```

This target runs, in order:

1. `scripts/setup_env.sh` — checks Python + pip, installs `requirements.txt`.
2. `python scripts/run_demo.py --epochs 100 --samples 4000` — generates dataset, trains PINN, evaluates, writes figures.
3. `bash scripts/validate_spice.sh` — runs notebook 07 via `jupyter nbconvert --execute`, producing `data/exports/spice_validation.{json,npz}` and figures.
4. `jupyter nbconvert --execute notebooks/08_Biomedical_Case_Study.ipynb` — writes `data/exports/biomedical_results.json`.
5. `pytest tests/ -v` — all 46 unit tests.

Expected wall-clock: **~20 min on a recent laptop CPU**. Lower `--samples` and `--epochs` for a faster spot-check.

## 4. SPICE-in-the-loop reproduction (ngspice + SKY130)

The default `make reproduce` runs notebook 07 in **fallback mode** (analytical oracle) if ngspice + SKY130 are not found. To run the full SPICE validation:

```bash
# 1. Install ngspice 46 from source
git clone --depth 1 --branch ngspice-46 https://git.code.sf.net/p/ngspice/ngspice
cd ngspice && ./autogen.sh && ./configure --enable-xspice && make -j4 && sudo make install

# 2. Install SKY130 PDK at the pinned commit
git clone https://github.com/google/skywater-pdk
cd skywater-pdk && git checkout f70d8ca
git submodule init libraries/sky130_fd_pr/latest && git submodule update
make timing
export PDK_ROOT=$(pwd)/..

# 3. Re-run make reproduce — notebook 07 auto-detects ngspice + PDK_ROOT
make reproduce
```

Alternatively, the [IIC-OSIC-TOOLS](https://github.com/iic-jku/iic-osic-tools) Docker image ships both pinned — mount this repo into `/workspace` and run `make reproduce` inside.

## 5. Expected artefacts

After `make reproduce` the following files **must exist** (CI asserts on their presence):

```
data/checkpoints/best_model.pt
data/processed/sar_dataset.pt
data/exports/spice_validation.json
data/exports/spice_validation.npz
data/exports/metastability_mc.json
data/exports/metastability_mc.npz
data/exports/biomedical_results.json
assets/figures/spice_dac_overlay.png
assets/figures/spice_parity_vdac.png
assets/figures/metastability_mc_tail.png
assets/figures/biomedical_report_card.png
assets/figures/biomedical_fom_vs_sota.png
```

## 6. Where each README claim is produced

See [`claim_evidence_matrix.csv`](claim_evidence_matrix.csv) for a full row-by-row mapping.

## 7. Known failure modes

- **`jupyter lab` complains about `attrs`.** Use `jupyter notebook` instead, or `pip install --upgrade attrs`.
- **ngspice segfaults on SKY130 `.lib` include.** Use ngspice 46+; earlier versions have a tt/ff corner-handling bug.
- **Colab runs out of RAM during dataset generation.** Drop `--samples` from 8,000 to 2,000 — metrics stay within 3%.

## 8. Contacting the author

- PR: <https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/pull/172>
- Author: Ayan Biswas, Purdue University — `ayanb@purdue.edu`
