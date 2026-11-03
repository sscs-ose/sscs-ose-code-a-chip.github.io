# SiliconForge

Project repository: https://github.com/Waleed99i/chipathon-2026-systolic-ip-core/tree/a34-rtl-fix-pd

SiliconForge is a parameterized systolic AI accelerator IP-core design developed for the IEEE SSCS PICO Open-Source Chipathon and presented as part of the Code-a-Chip at ISSCC 2027. The project targets a 4×4 processing-element array in GF180MCU and focuses on efficient matrix-multiply acceleration using a structured dataflow architecture, approximate arithmetic, and reusable RTL blocks.

## Project overview

The design organizes multiply-accumulate operations into a regular two-dimensional array: operands move between neighboring processing elements while partial sums stay local. The notebook covers:

- Architecture, pin assignment and packet interface,
- RTL organization of the MAC, processing element, counters, feeders, ready-valid block, datapaths and chip wrapper,
- MAC accuracy analysis of the approximate multiplier,
- Functional simulation results with a reproducible module-check package,
- Physical design in GF180MCU.

## Results at a glance

| Item | Result |
|---|---|
| Functional module checks | All listed checks pass (MAC, counter, PE, ready-valid, feeder, serializer, output datapath) |
| Physical design | 1.675 mm × 1.675 mm block, LibreLane flow plus a small ECO |
| Timing | 0 setup and 0 hold violations in all 9 corners at a 45 ns clock (22.2 MHz) |
| Sign-off | DRC, LVS and antenna clean |
| Gate-level check | Final netlist matches RTL bit for bit in 33/33 matrix cases |

## Team members

| Team member | Affiliation | Contribution |
|---|---|---|
| Muhammad Waleed Akram | University of Engineering and Technology, Lahore | Team lead; RTL, verification, interfaces and chip wrapper |
| Abdul Muiz | University of Engineering and Technology, Lahore | Systolic top RTL, verification and optimization |
| Rumali Siddiqua | University of Virginia, USA | Physical design and designated travel representative |
| Nur Cahyo Ihsan Prastyawan | Universitas Gadjah Mada, Indonesia | MAC RTL, verification and FPGA synthesis |

## Designated travel representative

Rumali Siddiqua  
University of Virginia, USA

## Project contact

Muhammad Waleed Akram  
Email: waleedakram059@gmail.com

or alternatively:

rumalisiddiqua@gmail.com

## Notebook

Notebook file: `SiliconForge_Code_a_Chip.ipynb`

All figures, tables and results are saved in the notebook, so it can be read without running anything. Figure cells store their picture inside the cell; running one redraws the same picture.

## How to run the notebook

The notebook runs top to bottom in Google Colab (use the badge at the top of the notebook) or locally.

Local setup:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install jupyterlab ipykernel numpy matplotlib pandas
jupyter lab ISSCC27/submitted_notebooks/SiliconForge/SiliconForge_Code_a_Chip.ipynb
```

Requirements:

- Python 3.10 or newer (Colab's default works)
- Jupyter with the packages above
- `git` and internet access for Section 16, which downloads the pinned layout files from branch `a34-rtl-fix-pd` and installs its own pinned analysis packages
- Optional: Icarus Verilog 12 (`sudo apt-get install iverilog`) to rerun the Section 15 module checks. Without it, that cell reports that the simulations were skipped and the saved results remain.

### What each part reproduces

- **Sections 1–14:** design description and saved results.
- **Section 15:** reruns the module checks from an RTL snapshot embedded in the notebook (branch `a34-rtl-fix-pd`, commit `13bd466`). Save the notebook as `SiliconForge_Code_a_Chip.ipynb` in the working folder first, as described in the notebook.
- **Section 16:** physical design analysis of the final layout at a pinned commit on branch `a34-rtl-fix-pd`; its first cell explains the setup.

## License

Apache-2.0. See `LICENSE`.

## Notes

This README is intended to help reviewers and collaborators understand the project quickly. The notebook is the primary source of technical detail, while the repository context provides the supporting design artifacts and documentation.
