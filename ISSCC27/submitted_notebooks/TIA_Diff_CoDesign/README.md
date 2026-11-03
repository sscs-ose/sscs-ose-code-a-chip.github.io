# TIA passive–active co-design

Open `TIA_CoDesign.ipynb` from this directory. Its figures and reported tables are embedded. The default executable cells inspect the submitted design and supplied models without running EM, training or optimization.

## Contents

- `code/`: layout generation, full-port openEMS, data preparation, residual-MLP training, joint optimization, circuit verification and plotting.
- `models/`: transformer and spiral surrogate checkpoints, with normalization, protected partitions and training reports.
- `data/`: geometry and partition definitions, search bounds and full-precision final design. These are configuration records, not EM datasets.
- `tools/`, `assets/`, `licenses/`: installation scripts, plotting font and source notices.

Raw GDS, Touchstone responses, response arrays, external figures, PDK files and archived optimization runs are excluded. New calculations write their outputs under `runs/`.

## Environment

Use Linux and Python 3.12. Install IHP-Open-PDK separately at the revision in `data/source_versions.json`, then set:

```bash
export TIA_PDK_ROOT="/path/to/IHP-Open-PDK"
```

The native build requires a C/C++ compiler, CMake, Make, Git, curl, tar and GMP development headers/libraries. The notebook gives the pinned toolchain versions and setup commands. To build the toolchain and compile the external PDK models:

```bash
bash tools/setup_environment.sh
source tools/activate.sh
python -m ipykernel install --user --name tia-codesign --display-name "TIA co-design"
```

For model inference and package checks alone, install `requirements.txt` in a Python environment; native EM/SPICE tools and the PDK are not required for those checks.

```bash
python code/workflow.py check --package-only
```

## Run the workflow

Set the flags in the notebook's first executable cell, then run the notebook in order:

| Flag | Operation |
|:--|:--|
| `RUN_GDS` | Generate the six transformer examples. |
| `RUN_EM` | Regenerate the transformer and spiral datasets and prepare their recorded partitions. |
| `RUN_TRAINING` | Fit both surrogate ensembles from the regenerated arrays. Select `cpu` in `training_devices` if CUDA is unavailable. |
| `RUN_OPTIMIZATION` | Start a fresh joint search using the selected checkpoints. |
| `RUN_VERIFICATION` | Independently EM-evaluate all three selected passives, replay the circuit and reconstruct performance and eye figures. |

With only `RUN_VERIFICATION=True`, the submitted final point is recomputed using the supplied surrogates before generating its three new EM networks. With `RUN_OPTIMIZATION=True`, the workflow uses only the new campaign's candidates. Newly trained checkpoints require a new optimization before verification. The spiral-domain binding records their identities while retaining the specified geometry and network limits.

The search starts with 22 variables and can expand to 23 and 25. It permits up to five random starts, followed by up to five conditional starts from the best valid candidate found within those random starts. Full details and acceptance conditions are in Section 7. The surrogate bandwidth threshold is 34 GHz; independent EM verification requires bandwidth greater than 32 GHz and all remaining circuit and voltage limits. Verification can perform the documented active refinement on the same three newly evaluated passive networks.

Keep existing run directories and choose fresh output paths for another calculation. Reconstructed figures and objective curves use those new run records. Embedded figures remain the recorded experiment until explicitly replaced.

To reconstruct the surrogate learning/test figures after regenerating the data, run `python code/surrogate_figures.py`. Add `--transformer-training runs/transformer_training --spiral-training runs/spiral_training` to use newly trained models and their learning records. Final circuit figures are reconstructed automatically after verification.
