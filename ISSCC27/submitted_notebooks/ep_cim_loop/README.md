# An Automated Open-Source Design Loop for Analog Compute-in-Memory: On-Chip Equilibrium-Propagation Inference and Training, from Network Training to a 1T1R RRAM Chip Layout in SKY130

Code-a-Chip (CaC) notebook: equilibrium propagation (EP) on a 1T1R RRAM crossbar chip. One Jupyter notebook, [`ep_cim_loop.ipynb`](ep_cim_loop.ipynb), runs the whole design loop from top to bottom.

## Authors
**Seokjin Oh, Jinzhan Li, and Suin Yi†**<br>
Department of Electrical and Computer Engineering, Texas A&M University, College Station, TX 77843, USA<br>
seokjindaveoh@tamu.edu, jl90@tamu.edu, yisuin@tamu.edu<br>
† Corresponding author: Suin Yi (yisuin@tamu.edu)

**Contributions**
- **S. Oh** — original author of the EP circuit implemented here (Micromachines 2023 [3]) and of its weight-update circuit (Nanomaterials 2025 [4]). Planned this chip and its design, defined the automated design flow, and implemented it end to end: network training on the circuit model, SPICE deck generators and circuit simulation, analog and array layout generators, digital RTL and the Yosys + OpenROAD flow, chip netlist, placement, routing, pad ring, DRC / LVS signoff, and the notebook.
- **J. Li** — verification of the automated design loop; data and loop verification of the network's inference and training.
- **S. Yi** — supervision.

## What this work is about
- **Equilibrium propagation (EP)** trains a network with local rules: each weight changes from the voltages at its own two ends, measured once in a free phase and once in a slightly nudged phase [1, 2].
  Backpropagation needs a separate global backward pass through the whole network; EP does not, which makes it attractive for energy-efficient on-chip learning.
- **The catch in software**: each EP step needs the equilibrium of the network (the minimum of its energy), which a computer has to find with an iterative numerical solver for every image.
- **In a circuit** this step disappears: a resistive network settles to that equilibrium by itself (Kirchhoff's laws), so the cost that makes EP slow in software is paid by physics [2, 5].
- **Main content: EP of Scellier and Bengio 2017 [1] on a chip, with the architecture of two works together** — the deep resistive network (DRN) of Scellier 2024 [5] for the network structure, and the memristor-crossbar EP circuit of S. Oh et al., *Micromachines* 2023 [3] (cited by 21, Google Scholar, Oct. 2026) for the circuit: two 1T1R crossbars (free and nudge), diode-clamp neurons, and the sign-based weight update with a fixed conductance step. The weight-update circuit follows [4] (cited by 4).
- **This notebook** turns that architecture into an **automated design loop**:
  network training on the circuit model → SPICE checks of every block → layout generators → digital blocks from RTL → chip assembly → DRC / LVS, all with open-source tools.

**What the loop produces** (details and numbers in section 14 of the notebook)
1. train the EP network directly on the 1T1R crossbar circuit model (MNIST digits 0/1/4, 7×7 binary inputs, 5-bit RRAM cells; PyTorch, CPU),
2. simulate the analog blocks, the weight-update block and the chip read deck with Xyce (all SPICE runs use Xyce),
3. generate the analog and array layouts with Python + KLayout (1T1R 128 × 64 array, analog drivers, weight-update block, test patterns, pad frame),
4. rebuild the four digital blocks from RTL with Yosys + OpenROAD (block DRC, LVS and gate-level simulation),
5. build the chip netlist and placement, route the nets between blocks with OpenROAD, add the pad ring,
6. check the core and the die with Magic and Netgen: LVS "Circuits match uniquely", DRC 0 violations after review (section 12).

## Folder
```
ep_cim_loop/
├── ep_cim_loop.ipynb            the notebook (run this)
├── README.md, LICENSE
├── env/                       tool setup: Dockerfile, requirements.txt, colab_setup.sh, setup.sh
├── weights/                   saved network weights (nostab_5bit.npz)
├── results/                   saved runs: time tables, tool versions, DRC / LVS summaries
└── src/
    ├── cac_ep/ep/                       EP training (EPConfig, EPNetwork, fit)              section 3
    ├── cac_ep/sim/ep_dr/
    │   ├── circuit.py, solver.py, data.py  circuit model, Newton solver, MNIST loader          sections 2–3
    │   ├── real_circuit/                   SPICE deck generators (weight-update block, chip)   sections 5, 7
    │   ├── layout/                         analog and array layout generators                  sections 5, 8
    │   ├── digital/, digital_oss/          RTL, testbenches, Yosys + OpenROAD flow             sections 4.3, 6, 8
    │   ├── layout/top/                     chip netlist, placement, routing, pad ring          sections 9–11
    │   └── opensrc/                        Magic / Netgen signoff, Xyce deck converters        sections 7, 12
    ├── cac_ep/sim/ep_demo/              SkyWater 5 V device models, ReRAM Verilog-A model
    └── sern_hog_classab_opamp/             op-amp layout generator                             section 5.8
```

| Path | Content |
|---|---|
| `ep_cim_loop.ipynb` | the notebook (executed; all outputs and figures saved) |
| `env/Dockerfile` | Docker image: IIC-OSIC-TOOLS 2026.10 (all EDA tools) + pinned Python packages + SKY130 PDK `c6d73a35` + this folder |
| `env/requirements.txt` | pinned Python packages (CPU PyTorch) |
| `env/colab_setup.sh` | Google Colab install (prebuilt Xyce bundle + public binaries), called by the setup cell |
| `env/setup.sh`, `env/environment.yml` | install without Docker and without root (user space), called by the setup cell |
| `env/run_apptainer.sh` | the Docker image steps with Apptainer / Singularity (HPC clusters without Docker) |
| `src/cac_ep/ep/` | EP training code (`EPConfig`, `EPNetwork`, `fit`) |
| `src/cac_ep/sim/ep_dr/` | circuit model and solver, SPICE deck generators (`real_circuit/`), layout generators (`layout/`), chip netlist / placement / routing / die (`layout/top/`), digital flow (`digital_oss/`), signoff scripts (`opensrc/`), notebook helpers (`layout/top/oss_nb/tools/`) |
| `src/sern_hog_classab_opamp/`, `src/cac_ep/sim/ep_demo/` | op-amp layout generator; SkyWater 5 V device models and the ReRAM Verilog-A model |
| `weights/` | saved network weights (`nostab_5bit.npz` = submitted, seeds 0 / 1 / 2) |
| `results/` | saved runs: time tables, tool versions, DRC / LVS summaries |

## How to run

### Which way to choose
| What you want | Recommended way | Why |
|---|---|---|
| **Look through the flow** — QUICK mode (about 30 min) | any way below: Docker, Google Colab, or Linux without Docker | QUICK checks every step at block level; small tool-version differences do not change what you see |
| **Reproduce the full demo** — FULL mode, with or without training | **Docker (strongly recommended)** | the image pins every tool to the versions that made the saved results (table "Tool versions"). Other ways install other builds of Magic, Netgen, OpenROAD and Yosys, so DRC counts, the synthesized digital netlists and the chip-level LVS can differ from the saved ones |
| **Only read** | open the notebook on GitHub | it is saved with all outputs and figures |

### Docker: set up and run (step by step)

**1. Install Docker** (once)
- **Linux (x86_64)** — Docker Engine:
  ```bash
  curl -fsSL https://get.docker.com | sh       # or your distribution's docker package
  sudo usermod -aG docker $USER                # run docker without sudo; log out and in again
  docker run --rm hello-world                  # check
  ```
- **Windows 10 / 11** — Docker Desktop with the WSL 2 backend; run the commands below in a WSL (Ubuntu) terminal.
- **macOS with an Intel CPU** — Docker Desktop.
- **Apple silicon / other ARM64** — the image also builds natively (ARM64 build of the same base image) and QUICK runs, but the digital synthesis differs from x86_64 and the chip LVS does not match the saved netlist; for FULL use an x86_64 machine (or `docker build --platform linux/amd64 ...`, emulated and much slower).
- **Resources** (Docker Desktop → Settings → Resources): at least 4 CPUs (16 recommended for FULL), 16 GB memory, 40 GB free disk.

**2. Get this folder**
```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io code-a-chip
git -C code-a-chip sparse-checkout set ISSCC27/submitted_notebooks/ep_cim_loop     # only this folder
cd code-a-chip/ISSCC27/submitted_notebooks/ep_cim_loop
```

**3. Build the image** (once; about 10–20 min and 18 GB, mostly the base image download)
```bash
docker build -t ep_cim_loop -f env/Dockerfile .
```
What the build does (`env/Dockerfile`):
1. starts from `hpretl/iic-osic-tools:2026.10` — all EDA tools (Yosys, OpenROAD, Magic, Netgen, Xyce, Icarus Verilog, KLayout);
2. installs the pinned Python packages (`env/requirements.txt`, CPU PyTorch) into `/opt/venv`;
3. downloads the SKY130 PDK build `c6d73a35` with volare into `/home/designer/pdk/volare`;
4. copies this folder to `/home/designer/ep_cim_loop`.

**4a. Run with Jupyter**
```bash
docker run --rm -p 127.0.0.1:8888:8888 ep_cim_loop
```
Open <http://localhost:8888/lab/tree/ep_cim_loop.ipynb>. In the second cell choose the mode — `MODE = 'quick' | 'full'`, `TRAIN = 'load' | 'quick' | 'full'` (table below) — then *Run → Run All Cells*.
The setup cell finds every tool on `PATH` and installs nothing. Outputs stay inside the container; use 4b to keep them.

**4b. Run without Jupyter, keep all outputs on the host**
```bash
mkdir -p out
docker run --rm -v "$PWD/out:/home/designer/out" ep_cim_loop \
  python3 -m papermill ep_cim_loop.ipynb /home/designer/out/ep_cim_loop_out.ipynb \
  -p MODE full -p TRAIN full -p WORK /home/designer/out/work
```
`./out` then holds the executed notebook, the time table (`work/times.md`), the figures (`work/figs/`) and every generated GDS / DEF / netlist / DRC / LVS file. Use `-p MODE quick -p TRAIN load` for the 30-min run.

**5. Check that the run is good**
- the last cell prints the time table and `0 failed`;
- section 3: "new weights vs submitted weights ... identical" (with `TRAIN='full'`);
- section 12: core and die LVS "Circuits match uniquely".

**Troubleshooting**
| Message | Fix |
|---|---|
| `permission denied ... docker.sock` | add your user to the `docker` group (step 1) and log in again |
| files in `./out` belong to root | `sudo chown -R $USER out` after the run (the container runs as its own user; do not add `--user`, the scripts update files inside the image) |
| port 8888 already in use | `-p 127.0.0.1:8889:8888`, then open port 8889 |
| downloads fail behind a proxy | `docker build --build-arg http_proxy --build-arg https_proxy ...` and `docker run -e http_proxy -e https_proxy ...` |
| `no space left on device` | free disk with `docker system prune`; the image needs about 18 GB |

**HPC cluster without Docker (Apptainer / Singularity)** — the same image steps run with Apptainer; tested on a cluster node with a fresh account (QUICK, 0 failed):
```bash
bash env/run_apptainer.sh ../cac_run quick load      # or: full full  (run folder outside this folder)
```
The script pulls the base image from Docker Hub, repeats steps 2–4 of the Dockerfile in user space and runs the notebook with papermill (outputs in `../cac_run/home/out`). If the compute nodes have no direct internet, load the site's web proxy first (`http_proxy`, `https_proxy`).

### Other ways (QUICK)
- **Google Colab** — [open the notebook in Colab](https://colab.research.google.com/github/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/ep_cim_loop/ep_cim_loop.ipynb) and choose *Run all*. The setup cell takes this folder from the official Code-a-Chip repository (sparse checkout; before the pull request is merged, from the submission fork), downloads a prebuilt Xyce bundle (a release file, 101 MB, too large for the repository) and installs the other tools with apt / conda / pip (`env/colab_setup.sh`).
- **Linux without Docker and without root** — `pip install --user -r env/requirements.txt`, then run the notebook; the setup cell installs the tools in user space (`env/setup.sh`: Magic, Netgen, OpenROAD, Yosys and Icarus Verilog from conda-forge / public builds, the PDK, and a source build of Xyce, about 2 h once). Tool builds differ from the Docker image, so use it for QUICK.

## Modes and measured times
One cluster node, 16 cores, 64 GB, in the Docker image (run with Singularity, same layers as `env/Dockerfile`).

| Mode | Parameters | What runs | Time |
|---|---|---|---:|
| **QUICK** | `MODE=quick TRAIN=load` | saved weights; Xyce weight-update block; all layout generators; four digital blocks with Yosys + OpenROAD; netlist, placement, routing, pad ring; core + die LVS; DRC of the array block | 29 min |
| **FULL** | `MODE=full TRAIN=load` | QUICK + Xyce chip read deck + Xyce read circuit on all 3,097 test images + DRC of the full core and die | 112 min |
| **FULL + training** | `MODE=full TRAIN=full` | FULL + EP training (seed 0, 165,000 training images); the new weights are compared with the saved weights | 144 min |

The step-by-step times are in `results/` and at the end of the notebook.

## Requirements
- Disk: base image 3.9 GB (compressed) + Python packages 0.9 GB + PDK 2.2 GB; work folder 0.3 GB (QUICK) to a few GB (FULL).
- RAM: 16 GB is enough. Internet on the first run (MNIST, PDK and Python packages).
- On an HPC cluster whose compute nodes have no direct internet, set the site's web proxy (`http_proxy`, `https_proxy`) before the first run and pass it into the container, e.g. `docker run -e http_proxy -e https_proxy ...`; with Apptainer / Singularity, export `APPTAINERENV_http_proxy` and `APPTAINERENV_https_proxy`.

## Tool versions (Docker image)
| Tool | Version |
|---|---|
| Base image | `hpretl/iic-osic-tools:2026.10` |
| OpenROAD, Magic, Netgen, KLayout | 26Q4-407, 8.3.685, 1.5.324, 0.30.12 |
| Xyce | 7.10 |
| Yosys, Icarus Verilog | 0.70, 14.0 (from the image) |
| Python, PyTorch (CPU), NumPy, Matplotlib | 3.12.3, 2.5.1, 2.2.6, 3.11.2 |
| SKY130 PDK | open_pdks `c6d73a35` (volare) |

## Limitations
- The RRAM write chip deck runs in Xyce with the SkyWater ReRAM Verilog-A compiled as a Xyce plug-in; the plug-in is built separately and is not part of the setup yet, so the notebook reports the stored SET / RESET results.
- Parasitic extraction with Magic covers the array and the input driver; the flat extraction of the whole core does not finish yet.
- Magic has no density check.

## References
1. B. Scellier and Y. Bengio, "Equilibrium propagation: bridging the gap between energy-based models and backpropagation," *Frontiers in Computational Neuroscience*, vol. 11, 24, 2017.
2. J. Kendall, R. Pantone, K. Manickavasagam, Y. Bengio, and B. Scellier, "Training end-to-end analog neural networks with equilibrium propagation," arXiv:2006.01981, 2020.
3. **S. Oh, J. An, S. Cho, R. Yoon, and K.-S. Min, "Memristor crossbar circuits implementing equilibrium propagation for on-device learning," *Micromachines*, vol. 14, no. 7, 1367, 2023, doi:10.3390/mi14071367 (cited by 21, Google Scholar, Oct. 2026) — the circuit implemented in this work.**
4. S. Oh, R. Yoon, and K.-S. Min, "Defect-tolerant memristor crossbar circuits for local learning neural networks," *Nanomaterials*, vol. 15, no. 3, 213, 2025, doi:10.3390/nano15030213 (cited by 4, Google Scholar, Oct. 2026) — weight-update circuit.
5. B. Scellier, "A fast algorithm to simulate nonlinear resistive networks," *Proc. ICML*, 2024 — deep resistive network (DRN).
6. R. Hogervorst, J. P. Tero, R. G. H. Eschauzier, and J. H. Huijsing, "A compact power-efficient 3 V CMOS rail-to-rail input/output operational amplifier for VLSI cell libraries," *IEEE J. Solid-State Circuits*, vol. 29, no. 12, pp. 1505–1513, 1994.
7. SkyWater SKY130 PDK (open_pdks) and its ReRAM cell model `sky130_fd_pr_reram__reram_cell`.
8. IIC-OSIC-TOOLS (H. Pretl et al., JKU), Yosys, OpenROAD, Magic, Netgen, Xyce, Icarus Verilog, KLayout, volare.

## License
Apache License 2.0, see [`LICENSE`](LICENSE). Copyright 2026 the authors.
Third-party files keep their licenses: SkyWater SKY130 device models and the ReRAM Verilog-A model (Apache-2.0), open_pdks cell libraries copied in `src/` (Apache-2.0).
