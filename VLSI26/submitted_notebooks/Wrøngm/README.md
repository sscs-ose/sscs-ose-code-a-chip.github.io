
<a href="https://colab.research.google.com/drive/1q6r7tg8RoyLBaMS3b7EONwkPCBzEM2c1?usp=sharing" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab Need to change before final submission"/></a>

---

# $R_{on}/g_m$ Based Design Methodology for Dynamic Amplifiers

> **VLSI 2026 Code-a-Chip Competition**  
> A proof-of-concept implementation of the $R_{on}/g_m$ design methodology for inverter-based dynamic amplifiers in the IHP SG13G2 130 nm BiCMOS process.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PDK](https://img.shields.io/badge/PDK-IHP%20SG13G2%20130nm-orange)](https://github.com/IHP-GmbH/IHP-Open-PDK)
[![Simulator](https://img.shields.io/badge/Simulator-ngspice%2045.2-green)](https://ngspice.sourceforge.io/)
[![Competition](https://img.shields.io/badge/VLSI%20CAC-2026-red)](https://sscs.ieee.org/membership/awards/ieee-sscs-code-a-chip-travel-grant-awards/)

---

## 👥 Team

<table>
  <thead>
    <tr>
      <th>Name</th>
      <th>Affiliation</th>
      <th align="center">IEEE</th>
      <th align="center">SSCS</th>
      <th>Contact</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Nithin P</strong></td>
      <td>IIT Gandhinagar</td>
      <td align="center">Yes</td>
      <td align="center">Yes</td>
      <td><a href="mailto:nithinpurushothama@gmail.com">nithinpurushothama@gmail.com</a></td>
    </tr>
    <tr>
      <td><strong>Pramoda S R</strong></td>
      <td>B.Tech, VTU</td>
      <td align="center">—</td>
      <td align="center">—</td>
      <td><a href="mailto:pramoda9.2.2004@gmail.com">pramoda9.2.2004@gmail.com</a></td>
    </tr>
    <tr>
      <td><strong>S Suyajnaa Jagannath Gowda</strong></td>
      <td>B.Tech, VTU</td>
      <td align="center">—</td>
      <td align="center">—</td>
      <td><a href="mailto:suyajnaa@gmail.com">suyajnaa@gmail.com</a></td>
    </tr>
    <tr>
      <td><strong>Runpeng Gao</strong></td>
      <td>PhD, Oregon State University</td>
      <td align="center">Yes</td>
      <td align="center">Yes</td>
      <td><a href="mailto:rppgao@gmail.com">rppgao@gmail.com</a></td>
    </tr>
    <tr>
      <td><strong>Praveen Kumar Venkatachala</strong></td>
      <td>PhD, Oregon State University</td>
      <td align="center">Yes</td>
      <td align="center">Yes</td>
      <td><a href="mailto:vpravin.8@gmail.com">vpravin.8@gmail.com</a></td>
    </tr>
    <tr style="background-color: #f0f0f0;">
      <td><strong>🎓 Prof. Madhav K Pathak</strong></td>
      <td>Asst. Professor, EE Dept, IIT Gandhinagar</td>
      <td align="center">Yes</td>
      <td align="center">Yes</td>
      <td><a href="mailto:madhav.pathak@iitgn.ac.in">madhav.pathak@iitgn.ac.in</a></td>
    </tr>
  </tbody>
</table>


---

## Running the Notebook

### Option 1 - Google Colab (Recommended)

The Reviwers are highly recommended to use the Colab version of this work. This doesnt require any setup.

---
**Google Colab Link**: https://colab.research.google.com/drive/1q6r7tg8RoyLBaMS3b7EONwkPCBzEM2c1?usp=sharing

---

1. Click the **Open in Colab** badge at the top of this file
2. Sign in with any Google account (free tier is sufficient)
3. Go to **Runtime → Run all** (or press `Ctrl+F9`)
4. If prompted with *"This notebook was not authored by Google"* → click **Run anyway**
5. Wait for execution to complete

| Phase | What happens | Est. time |
|:--|:--|:--|
| Steps 1–3 | Install build tools, download IHP SG13G2 model files, compile PSP 103.6 NQS via OpenVAF | ~2 min |
| Step 4 | Build ngspice 45.2 from source with `--enable-osdi` | ~9 min |
| Steps 5–6 | Generate 15 SPICE netlists and run all simulations | ~1 min |
| Steps 7+ | Load LUT CSVs, generate design plots, launch interactive dashboards | ~30 s |

> **Total: ~10–12 minutes.** While the notebook builds and simulates, read through the theory sections - they provide the context needed to interpret the plots and dashboard outputs.

To re-run a single cell: click it and press **Shift + Enter**.  
If execution stalls or an error occurs: **Runtime → Restart and run all**.

---

### Option 2 - Local / Jupyter

Install dependencies:

```bash
pip install plotly pandas numpy scipy gdown requests kaleido ipywidgets
```

Run cells top-to-bottom. An internet connection is required for PDK model files and simulation data.  
If not using Colab, update `data_path` in **Cell 27** to point to your local CSV directory.

> **Note:** ngspice must be built from source with `--enable-osdi` to load the PSP 103.6 NQS model. The `apt` package (v36) does not support OSDI. See Steps 1–4 in the notebook for the build sequence.

---

## Abstract

This work presents an $R_{on}/g_m$-based design methodology for inverter-based dynamic amplifiers (IBA), addressing a fundamental gap in existing approaches where the large-signal RC settling phase governed by the final-stage device on-resistance $R_{on}$ remains uncharacterised until post-simulation.

Unlike the conventional $g_m/I_D$ methodology, which targets only the small-signal transconductance, the proposed approach simultaneously co-designs both settling phases through pre-characterised device look-up tables (LUTs) derived from parametric SPICE simulations in the IHP SG13G2 130 nm BiCMOS process. These LUTs capture $R_{on}/g_m$ as a function of device geometry, bias, and process corner, making worst-case corner behaviour and valid bias deadzone boundaries directly readable at the design entry stage without iterative simulation.

A head-to-head comparison with the $g_m/I_D$ methodology confirms that the $R_{on}/g_m$ approach achieves equivalent settling accuracy while substantially reducing design cycles and surfacing process-corner sensitivity upfront.

---

## Table of Contents
---

1. Introduction
2. Dynamic Amplifier
   - 2.1 Understanding Dynamic Amplifiers
   - 2.2 Error Behavior of Dynamic Amplifiers
   - 2.3 Ron/gm Based Design Methodology
3. Simulation Environment Setup
   - 3.1 Automated SPICE Netlist Generation
   - 3.2 Step 1 - Build Ngspice 45.2
   - 3.3 Step 2 - Download IHP SG13G2 Models
   - 3.4 Step 3 - Compile PSP 103.6 NQS
   - 3.5 Step 4 - Write .spiceinit
   - 3.6 Step 5 - Simulation Configuration
   - 3.7 Step 6 - Run All 15 Simulations
4. Design Plots for the Ron/gm Methodology
   - 4.1 $V_{bias}$ vs log($R_{on}$/$G_m$)
   - 4.2 $V_{bias}$ vs Width
   - 4.3 log($I_{peak}$) vs log($R_{on}/g_m$)
   - 4.4 $g_{m,bias}$ vs log($R_{on}/g_m$)
   - 4.5 $G_m$/$I_d$ vs log($R_{on}/g_m$)
   - 4.6 $V_{swing}$ vs log($R_{on}/g_m$)
5. IBA Design: gm/ID Methodology
   - 5.1 Gm/ID Characterisation and Design Helper
   - 5.2 Results
   - 5.3 Summary and Motivation for RAMPA
6. IBA Design: Ron/gm Methodology
   - 6.1 Ron/gm Design Helper
   - 6.2 Results
7. Comparative Analysis
8. References

---

## Key Features

- **Two-phase settling co-design** - large-signal RC phase ($R_{on}$) and small-signal exponential phase ($g_m$) designed simultaneously from a single LUT
- **Pre-simulation corner visibility** - SS/TT/FF worst-case $R_{on}$ and deadzone bias ranges ($V_{DZP}$, $V_{DZN}$) readable at design entry
- **15 parametric SPICE simulations** - automated netlist generation across 5 channel lengths × 3 process corners using ngspice 45.2 with OSDI support
- **Interactive design helpers** - live slider-based dashboards for both $R_{on}/g_m$ and $g_m/I_D$ operating point selection
- **Full PDK integration** - IHP SG13G2 PSP 103.6 NQS compact model compiled from Verilog-A via OpenVAF
- **Head-to-head comparison** - transient settling results for both methodologies side-by-side (Figures 10–18)

---

## Notebook Structure

| Section | What it covers |
|:--|:--|
| **Introduction** | OTA settling fundamentals, dynamic amplifier two-phase behaviour, motivation for $R_{on}/g_m$ |
| **Methodology** | $R_{on}/g_m$ design flow, LUT construction, deadzone analysis |
| **Simulation Setup** | ngspice 45.2 build, IHP SG13G2 PDK download, PSP model compilation, netlist generation |
| **LUT Generation** | 15 parametric SPICE runs (5L × 3 corners); CSV extraction |
| **Design Plots** | 6 interactive Plotly charts: $V_{bias}$, width, $I_{peak}$, $g_{m,bias}$, $g_m/I_D$, $V_{swing}$ vs $R_{on}/g_m$ |
| **$g_m/I_D$ Design** | IBA designed using conventional methodology as baseline (NMOS W=2.3 µm L=1 µm m=4; PMOS W=4.5 µm L=0.5 µm m=4) |
| **$g_m/I_D$ Helper** | Interactive dashboard: σ-normalised nearest-neighbour LUT search over $g_m/I_D$, $g_m/g_{ds}$ |
| **$g_m/I_D$ Results** | Settling waveforms, log error, $I_{out}$, $dV_{out}/dt$ - Figures 10–13 |
| **$R_{on}/g_m$ Design** | IBA designed using proposed methodology (NMOS W=3.3 µm L=1 µm m=4; PMOS W=6.1 µm L=0.5 µm m=4) |
| **$R_{on}/g_m$ Helper** | Interactive dashboard: LUT search over $(I_{bias},\, R_{on}/g_m,\, L)$ with corner selection |
| **$R_{on}/g_m$ Results** | Settling waveforms, log error, $I_{out}$, $dV_{out}/dt$ - Figures 15–18 |
| **Comparative Analysis** | Side-by-side methodology comparison table with advantages and limitations |

---


## Tool Stack

| Tool | Version | Role |
|:--|:--|:--|
| ngspice | 45.2 (source build) | SPICE simulator with OSDI runtime |
| OpenVAF | osdi_0.3 | Verilog-A → OSDI compiler |
| IHP SG13G2 PDK | Open-source | Process corner model libraries |
| Python | ≥ 3.10 | Notebook runtime |
| Plotly | Latest | Interactive design charts |
| ipywidgets | Latest | Live slider dashboards |
| gdown | Latest | Google Drive data download |

## PERFORMANCE SUMMARY AND COMPARISON WITH STATE-OF-THE-ART

<div style="overflow-x:auto; width:100%;">
<table style="width:100%; border-collapse:collapse; border-top:2px solid #000; border-bottom:2px solid #000; table-layout:fixed; font-family:'Times New Roman',serif; font-size:9pt;">
<colgroup><col style="width:28%;"><col style="width:24%;"><col style="width:24%;"><col style="width:24%;"></colgroup>
<thead>
<tr>
  <th style="text-align:left; padding:6px 7px; border-bottom:1px solid #000; font-weight:bold; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Design Criterion</th>
  <th style="text-align:center; padding:6px 7px; border-bottom:1px solid #000; font-weight:bold; background:#f0f0f0; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">$R_{on}/g_m$ <b>(This Work)</b></th>
  <th style="text-align:center; padding:6px 7px; border-bottom:1px solid #000; font-weight:bold; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">$g_m/I_D$ Methodology</th>
  <th style="text-align:center; padding:6px 7px; border-bottom:1px solid #000; font-weight:bold; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Conrad <i>et al.</i> [TCAS-I 2020]</th>
</tr>
</thead>
<tbody>

<!-- ── I ── -->
<tr><td colspan="4" style="background:#000; color:#fff; font-weight:bold; font-size:8.5pt; letter-spacing:.06em; padding:3px 8px; max-width:none;">I. &nbsp;METHODOLOGY</td></tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Design paradigm</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;">Analytical LUT<br><small><i>Physics-based; pre-characterised</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Analytical LUT<br><small><i>Small-signal only</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Simulation-based numerical optimizer<br><small><i>Cadence ADE XL</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Primary design parameter</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;">$R_{on}/g_m$<br><small><i>Couples large-signal + small-signal</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">$g_m/I_D$<br><small><i>Small-signal only</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">$m_{a1},\, m_{a2},\, m_{a3},\, I_{bias},\, R,\, C_{az}$<br><small><i>6 numerical params; no physical link</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Design entry stage</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;">Pre-simulation</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Pre-simulation<br><small><i>Partial — no large-signal info</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Requires full transient simulation per iteration</td>
</tr>

<!-- ── II ── -->
<tr><td colspan="4" style="background:#000; color:#fff; font-weight:bold; font-size:8.5pt; letter-spacing:.06em; padding:3px 8px; max-width:none;">II. &nbsp;SETTLING PHASE COVERAGE</td></tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Non-linear (large-signal / RC) settling characterized</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>Via $R_{on}$ in LUT; $\tau_{ls} = R_{on}C_L$</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>$R_{on}$ absent from $g_m/I_D$ framework</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Acknowledged as "not practical" [4]†</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Small-signal ($g_m C$) settling characterized</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>Via $g_{m,bias}$ in LUT; $BW = g_m/(2\pi C_L)$</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>Primary strength of $g_m/I_D$ methodology</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>Via rms error cost function</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Unified two-phase settling model</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>$R_{on}/g_m$ co-constrains both $\tau_{LS}$ and $\tau_{SS}$</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Small-signal-phase only</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>No time-budget allocation between phases</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Peak slew current $I_{peak}$ predicted pre-simulation</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>$I_{peak} \propto 1/(R_{on}/g_m)$; log-log scale slope $= -1$</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Post-optimization verification only</i></small></td>
</tr>

<!-- ── III ── -->
<tr><td colspan="4" style="background:#000; color:#fff; font-weight:bold; font-size:8.5pt; letter-spacing:.06em; padding:3px 8px; max-width:none;">III. &nbsp;PROCESS CORNER ROBUSTNESS</td></tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">TT / SS / FF corners visible at design entry</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>All 3 corners in LUT; SS worst-case directly readable</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>LUT can be corner-swept but $R_{on}$ not extracted</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>PVT excluded from optimizer loop‡</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Deadzone bias ($V_{DZN}$, $V_{DZP}$) determined pre-simulation</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>Per-corner, from $V_{bias}$ vs $R_{on}/g_m$ plot§</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Unknown without iterative transient corner sweeps</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>$V_{os}$ is one of 6 optimized params; corner sensitivity unknown a priori</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">SS-corner $R_{on}$ degradation visible a priori</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/></td>
</tr>

<!-- ── IV ── -->
<tr><td colspan="4" style="background:#000; color:#fff; font-weight:bold; font-size:8.5pt; letter-spacing:.06em; padding:3px 8px; max-width:none;">IV. &nbsp;DESIGN EQUATIONS AND PHYSICAL INSIGHT</td></tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Closed-form design equations available</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>$V_{bias} = V_{TH} + 2I_D/g_m$;<br>$g_{m,bias} \propto (R_{on}/g_m)^{-1/3}$;<br>$R_{on}/g_m \propto L^2/(W I_D)$</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>For small-signal: $G_m = 2\pi f C_L$;<br>$W = I_D / (I_D/W)|_{LUT}$</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Stability criterion exists but "not realizable" as design equation†</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Physical insight preserved throughout design</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>Every plot axis maps to a physical quantity</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>For small-signal operating point only</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Optimizer returns numbers; no physical link retained</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Subsumes $g_m/I_D$ methodology</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>$g_m/I_D$ readable from $g_m/I_D$ vs $R_{on}/g_m$ plot; reverse not possible</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">—</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/></td>
</tr>

<!-- ── V ── -->
<tr><td colspan="4" style="background:#000; color:#fff; font-weight:bold; font-size:8.5pt; letter-spacing:.06em; padding:3px 8px; max-width:none;">V. &nbsp;PRACTICAL DESIGN FLOW</td></tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">EDA tool requirement</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;">Open-source and Commercial tools<br><small><i>Any spice + Python/Matlab</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Spectre (LUT gen.)<br><small><i>Helper usable standalone</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Cadence Virtuoso + Spectre + ADE XL<br><small><i>Full commercial license stack</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Application-specific redesign required</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>LUT generated once per technology node</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>LUT reusable across applications</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>New testbench + cost function per application</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Cost function calibration required</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>Manual ×4 adjustment applied in paper¶</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">PVT robustness in design loop</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>SS/FF corner LUTs included by design</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Corner LUT possible; dynamic behavior not covered</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Excluded from optimizer; post-hoc Monte Carlo only‡</i></small></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;">Technology portability</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>15 ngspice sims re-characterize any PDK (~1 min)</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22" height="22"/><br><small><i>New Spectre LUT per node</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; white-space:normal; max-width:0;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22" height="22"/><br><small><i>Full optimizer rerun needed; 180 nm fails power target by 13×**</i></small></td>
</tr>
<!-- ── VI ── -->
<tr><td colspan="4" style="background:#000; color:#fff; font-weight:bold; font-size:8.5pt; letter-spacing:.06em; padding:3px 8px; max-width:none;">VI. &nbsp;DESIGN EXAMPLE RESULTS (IBA, T<sub>settle</sub> = 250 ns, UGB = 9.55 MHz (60 Mrad/s), C<sub>L,eff</sub> = 667 fF, IHP SG13G2 130 nm)</td></tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd;">$G_m$ target met (UGB = 9.55 MHz)</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/> $\approx 40\,\mu\text{S}$</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/> $\approx 40\,\mu\text{S}$</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/> 15-bit ENOB</td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd;">$I_{peak}$ range</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/><br><small><i> 14 $\mu$A(positive edge), -13.86 $\mu$A(negative edge)</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd;">$R_{on}$ known before transient simulation</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/><br><small><i>4 kΩ unit; 1 kΩ after ×4 multiplier</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/><br><small><i>Post-simulation discovery only</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd;">$V_{DZN}$ (NMOS deadzone) pre-simulation</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/><br><small><i>FF: 0.355 V | TT: 0.390 V | SS: 0.425 V</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px; border-bottom:0.5px solid #ddd;">$V_{DZP}$ (PMOS deadzone) pre-simulation</td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/><br><small><i>FF: 0.970 V | TT: 1.110 V | SS: 1.204 V</i></small></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/></td>
  <td style="text-align:center; padding:5px 7px; border-bottom:0.5px solid #ddd;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/></td>
</tr>

<tr>
  <td style="text-align:left; padding:5px 7px;">Extra transient sims needed to obtain $V_{DZ}$ and $R_{on}$</td>
  <td style="text-align:center; padding:5px 7px; background:#fafafa;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="22"/> <b>Zero</b></td>
  <td style="text-align:center; padding:5px 7px;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/><br><small><i>Multiple corner sweeps required</i></small></td>
  <td style="text-align:center; padding:5px 7px;"><img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="22"/><br><small><i>Full optimizer run per corner</i></small></td>
</tr>

</tbody>
</table>

<div style="font-size:8pt; line-height:1.7; border-top:0.75px solid #000; margin-top:5px; padding-top:4px;">
Pre-simulation $V_{bias}$ predictions were within <b>&plusmn;75 mV</b> of post-simulation values; $I_{peak}$ predicted within ~15%.
</div>

<p>† J. Conrad <i>et al.</i>: <i>"Unfortunately, Section II-B is not really practical for designing a RAMP… This makes a design-by-equation cumbersome and not realizable."</i> [TCAS-I 2020, Sec. II-C]</p>
<p>‡ J. Conrad <i>et al.</i>: <i>"PVT variations are not encountered during the circuit optimization, because this would require many transient simulations to evaluate one iteration of the optimizer."</i> [TCAS-I 2020, Sec. V-E]</p>
<p>§ Deadzone bias values read from the $V_{bias}$ vs. $\log(R_{on}/g_m)$ LUT plot at $R_{on}/g_m = 50 \times 10^6$ (per device, post-multiplier), $I_{bias} = 0.5\,\mu$A (unit cell), $I_{bias} = 2\,\mu$A (Overall IBA).</p>
<p>¶ J. Conrad <i>et al.</i>: <i>"the optimizer goal for the accuracy was readjusted ×4 smaller, i.e. 0.25 for the cost function."</i> [TCAS-I 2020, Sec. IV-B.3]</p>
<p>** J. Conrad <i>et al.</i>, Table II: 180 nm power cost function = 12.99 (target: 1.0), failing the power constraint by 13×.</p>
<p style="margin-top:6px;">
  <img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/happy.svg" width="16" height="16"/> = fully supported / available pre-simulation &nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/chennakeshavadasa/gmid_IHP130/refs/heads/main/Plots_Images/Notebook_Figs/sad.svg" width="16" height="16"/> = not available / requires post-simulation discovery
</p>
</div>
</div>

---

## References


[1] B. Hershberg, S. Weaver, K. Sobue, S. Takeuchi, K. Hamashita and U. -K. Moon, "Ring amplifiers for switched-capacitor circuits," 2012 IEEE International Solid-State Circuits Conference, San Francisco, CA, USA, 2012, pp. 460-462, doi: [10.1109/ISSCC.2012.6177090](https://doi.org/10.1109/ISSCC.2012.6177090).

[2] Venkatachala, Praveen Kumar. 2019. *[Design Considerations and Circuit Techniques for Robust Ring-Amplifiers](https://ir.library.oregonstate.edu/downloads/rr1724065)*. Oregon State University.

[3] Brooks, Lane & Lee, Hae-Seung. (2007). "A zero-crossing-based 8b 200MS/s pipelined ADC." *IEEE International Solid-State Circuits Conference, 2007. ISSCC 2007. Digest of Technical Papers*. 460-615. doi: [10.1109/ISSCC.2007.373493](https://doi.org/10.1109/ISSCC.2007.373493).

 [4] J. Conrad, P. Vogelmann, M. A. Mokhtar and M. Ortmanns, "Design Approach for Ring Amplifiers," in IEEE Transactions on Circuits and Systems I: Regular Papers, vol. 67, no. 10, pp. 3444-3457, Oct. 2020, doi: [10.1109/TCSI.2020.2986553](https://ieeexplore.ieee.org/document/9076616).

 [5] P. R. Kinget, "Scaling analog circuits into deep nanoscale CMOS: Obstacles and ways to overcome them," 2015 IEEE Custom Integrated Circuits Conference (CICC), San Jose, CA, USA, 2015, pp. 1-8, doi: [10.1109/CICC.2015.7338394](https://ieeexplore.ieee.org/document/7338394).

 [6] J. Annema, B. Nauta, R. van Langevelde and H. Tuinhout, "Analog circuits in ultra-deep-submicron CMOS," in IEEE Journal of Solid-State Circuits, vol. 40, no. 1, pp. 132-143, Jan. 2005, doi: [10.1109/JSSC.2004.837247](https://ieeexplore.ieee.org/document/1374997).

 [7] B. Razavi, Design of Analog CMOS Integrated Circuits, 2nd ed., McGraw-Hill, 2017. (Ch. 12 Switched-Capacitor Circuits).

 [8] Y. Chae and G. Han, "Low Voltage, Low Power, Inverter-Based Switched-Capacitor Delta-Sigma Modulator," in IEEE Journal of Solid-State Circuits, vol. 44, no. 2, pp. 458-472, Feb. 2009, doi: [10.1109/JSSC.2008.2010973](https://ieeexplore.ieee.org/document/4768910).

 ---

## License

Licensed under the [Apache 2.0 License](https://opensource.org/licenses/Apache-2.0).
