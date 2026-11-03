# SidecarCIM

SidecarCIM is an integer-only digital compute-in-memory (DCIM) macro with an
outlier sidecar, for 4-bit LLM inference on SKY130. It is an IEEE SSCS
Code-a-Chip entry for ISSCC 2027 by Bao Vo, University of Michigan (graduate
alumnus), under the Apache 2.0 license (`LICENSE`).

## Run the notebook

Open `SidecarCIM.ipynb` in Colab with the badge at the top of the notebook, or
run it locally with Python 3.10 or newer:

```bash
pip install numpy pandas matplotlib jupyter
jupyter nbconvert --to notebook --execute SidecarCIM.ipynb
```

Every cell reads saved files in this folder, so nothing is downloaded or
simulated, and a run takes well under a minute. If you set `RUN_FULL = True`
in the first code cell, the notebook also cross-checks its reference model
against `python/golden.py` (this needs PyYAML) and checks every case in the
stored test vectors, which takes about five minutes.
With `RUN_SIM = True` the notebook also simulates the final build's RTL
with cocotb and Icarus Verilog (installed if missing), which takes about a
minute.

## What is in this folder

| Path | Contents |
| --- | --- |
| `SidecarCIM.ipynb` | the notebook |
| `requirements.txt` | Python packages for the studies and testbenches (`pip install -r requirements.txt`) |
| `spec/spec.yaml` | every design parameter |
| `rtl/` | Verilog-2005 sources: dense array, sidecar, top level, 8-bit array, MAC baseline |
| `tests/` | cocotb and Icarus Verilog testbenches and the sign-off report `tests/report.md` |
| `python/` | the bit-exact reference `golden.py`, the quantization and accuracy studies, test vectors |
| `flow/` | LibreLane configurations and the PPA, power and render scripts |
| `results/` | PPA and accuracy tables, the waveform and layout render, and the scripts that make them |
| `results/signoff/` | the LibreLane sign-off reports (`metrics.json`, `manufacturability.rpt`) of all 11 layouts |
| `results/gds/sidecarcim_top_ff_pipe_s3.gds.gz` | GDS of the final SidecarCIM build (merge register, 3-bit shift) |

## Regenerating what is not shipped

The test vectors that the notebook does not read are left out to save space,
among them `dense8_random.npz` and the W6A4, W7A4, W8A4 and W4A8 sets.
`python python/vectors.py`, run from this folder, rewrites every file in
`python/vectors/`. The seeds are fixed, and a regeneration matched the
original arrays exactly. It needs numpy, PyYAML, pandas, pyarrow, torch and
transformers, and the first run downloads GPT-2 small and WikiText-2 from
Hugging Face.

Only the final SidecarCIM build's GDS is included. The other laid-out designs
are `sidecarcim_top_ff_pipe`, `sidecarcim_top_ff`, `sidecarcim_top_ff_par`,
`dcim_core_ff`, `dcim_w6a4_ff`, `dcim_w7a4_ff`, `dcim_w8a4_ff`,
`dcim_w4a8_ff`, `dcim_8bit_ff` and `mac_baseline`, plus the 128-row layouts in
`flow/p128/`. Each one is reproduced with LibreLane 3.0.16 from its
`config.json`:

```bash
librelane --docker-no-tty --dockerized flow/<design>/config.json
python3 flow/extract_ppa.py
```

Flow run directories and VCD files are not included either. The commands in
Sec. VIII of the notebook regenerate them; they need LibreLane in Docker, Icarus
Verilog, cocotb and Verilator.
