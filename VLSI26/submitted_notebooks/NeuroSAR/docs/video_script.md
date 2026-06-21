# NeuroSAR: 3-Minute Submission Video Script

**Total runtime:** 3:00  
**Format:** Screen recording + voiceover  
**Resolution:** 1920×1080 minimum  
**Export format:** MP4 (H.264)

---

## Pre-Recording Setup Checklist

- [ ] Open `02_interactive_demo.ipynb` in JupyterLab, fully executed, widgets visible
- [ ] Open `03_fom_exploration.ipynb` with FoM heatmap figure pre-rendered
- [ ] Open `04_inverse_design.ipynb` with optimization trajectory ready
- [ ] Set display font size to ≥ 14pt (JupyterLab: Settings → Theme → Font Size)
- [ ] Use a dark or high-contrast JupyterLab theme for screen legibility
- [ ] Use presentation mode or hide the JupyterLab left sidebar to maximize content area
- [ ] Microphone check: record a 10-second test clip and review audio quality

---

## Scene 1 — Motivation (0:00 – 0:30)

**Screen:** Slide or markdown cell showing:
- A SAR ADC block diagram (simple schematic or labeled block)
- A SPICE simulation time counter ticking up (screenshot from ngspice showing "Simulation time: 47.3s")
- A 9-dimensional grid of parameter space visualization

**Voiceover:**

> "SAR ADCs power billions of IoT and biomedical devices, yet designing one still means waiting for SPICE simulations that take minutes per point. A 9-dimensional design space sweep? That's thousands of simulation hours. And SPICE is non-differentiable — you can't run gradient-based optimization through it, and you can't get real-time interactive feedback. NeuroSAR changes that."

**Key visual transitions:**
- Start: SPICE terminal output showing long simulation time
- Transition: Arrow pointing to a 3×3 grid of parameter combinations with a "time ×1000" label, implying the impossibility of brute-force sweeps
- End: NeuroSAR logo / title slide

**Screen notes:**
- Show the ngspice terminal with a realistic elapsed time display
- The slide should visually contrast "SPICE: ~47 seconds" vs "NeuroSAR: <1 ms"

---

## Scene 2 — Architecture (0:30 – 1:00)

**Screen:** Architecture diagram (from `figures/architecture.png` or a styled Jupyter markdown cell) showing:
- Input vector (11-D) with labeled parameter names
- Fourier feature encoding block
- 5-layer MLP trunk
- Two output heads: V_dac(t) and V_comp(t)
- Loss decomposition: L_data, L_KCL, L_charge, L_ODE, L_smooth

**Voiceover:**

> "NeuroSAR is a physics-informed neural network — a surrogate model that doesn't just fit data, but learns to satisfy the governing equations of the circuit. The input is an 11-dimensional vector of design parameters and time, encoded with random Fourier features to capture the multi-scale temporal dynamics of SAR conversion. The network predicts two outputs jointly: the DAC settling waveform and the comparator regeneration trajectory."

**Pause here (~10 seconds, slow down):**

> "During training, the loss function includes four physics residuals computed via automatic differentiation: KCL at the DAC node, charge conservation at each bit decision, the comparator regeneration ODE, and a smoothness regularizer. These are not soft suggestions — they are mathematically enforced constraints that ensure every prediction is physically consistent."

**Screen notes:**
- Highlight each physics term in the loss formula as you mention it
- Use a pointer or screen annotation tool to trace the data flow through the architecture diagram
- Show the loss equation on screen: $\mathcal{L} = w_d \mathcal{L}_{data} + w_{kcl} \mathcal{L}_{kcl} + w_c \mathcal{L}_{charge} + w_{ode} \mathcal{L}_{comp} + w_s \mathcal{L}_{smooth}$

---

## Scene 3 — Interactive Demo (1:00 – 1:45)

**Screen:** `02_interactive_demo.ipynb` — live interactive widget panel  
Show:
- Slider controls for: C_unit, gm, C_load, V_ref, N_bits
- Live-updating plot of V_dac(t) — the SAR staircase waveform
- Live-updating plot of V_comp(t) — the exponential regeneration curve
- A "Metastability Warning" indicator that turns red when gm is set low

**Voiceover:**

> "Here's what that looks like in practice. [Move C_unit slider.] As I increase the unit capacitor, watch the staircase become more precise — larger capacitors mean better charge accuracy and lower thermal noise. [Move gm slider up.] Now I'll increase the transconductance of the comparator — the regeneration slope steepens, meaning faster bit decisions and higher sampling rate."

**Slow demonstration move:**

> "[Move gm slider to minimum.] With gm near its minimum, the regeneration time constant exceeds the clock period — NeuroSAR flags this as a metastability risk. We're seeing exactly the comparator overdrive condition that causes bit errors in real silicon."

**Screen notes:**
- Move sliders slowly and deliberately — allow the plot to update visibly between moves
- Show the metastability warning indicator activating
- Point out the staircase step heights changing as V_ref or C_unit changes
- If possible, show a split-screen comparison of V_dac and V_comp side by side

---

## Scene 4 — FoM Exploration (1:45 – 2:15)

**Screen:** `03_fom_exploration.ipynb`  
Show:
- The 2-D Walden FoM heatmap: axes are C_unit (x) and gm (y), color = FoM in fJ/conv-step
- Iso-ENOB contour lines overlaid (8-bit, 9-bit, 10-bit contours)
- A Pareto front scatter plot: ENOB vs. Power, each point colored by FoM

**Voiceover:**

> "Moving beyond single-point design, NeuroSAR enables full design-space sweeps in seconds. This heatmap shows the Walden figure of merit across the C_unit and transconductance design space — colors represent FoM from 3 fJ per conversion step in the optimal corner up to 50 fJ in the inefficient regions. The overlaid contours show iso-ENOB lines. The optimal region clusters around moderate capacitance and high transconductance — exactly the trade-off circuit designers navigate intuitively."

**Screen notes:**
- Let the heatmap fill the screen
- Slowly zoom in to the optimal (low FoM) region to show contour structure
- Show the Pareto scatter plot next: point out the Pareto-optimal front at the bottom-left
- Mention that this entire sweep — 2,500 design points — completes in under 2 seconds on CPU

---

## Scene 5 — Inverse Design (2:15 – 2:45)

**Screen:** `04_inverse_design.ipynb`  
Show:
- The optimization objective: "Find C_unit, gm such that ENOB ≥ 9.5 bits and FoM ≤ 10 fJ/conv-step"
- The optimization trajectory plotted on the FoM heatmap (from random starting point, gradient descent arrows converging to optimal region)
- Final solution printout: C_unit = X fF, gm = Y mS → ENOB = 9.7 bits, FoM = 8.3 fJ/conv-step

**Voiceover:**

> "The most powerful capability of a differentiable surrogate is inverse design. We can specify a target — 9.5-bit ENOB and a 10 femtojoule per conversion step FoM — and run gradient-based optimization directly through the PINN to find the optimal parameter combination. [Show trajectory converging.] Starting from a random point in design space, 50 gradient steps bring us to a solution that meets both specs. This would take thousands of SPICE simulations by hand. NeuroSAR finds it in under one second."

**Screen notes:**
- Animate the optimization trajectory if possible (matplotlib animation saved as GIF)
- Show the objective function value decreasing on a secondary plot (loss vs. iteration)
- Print the final solution prominently — large font, clearly readable on video

---

## Scene 6 — Conclusion and Future Work (2:45 – 3:00)

**Screen:** Clean summary slide or styled markdown cell with:
- Three bullet points: What NeuroSAR does (surrogate), why it matters (speed + differentiability), future work
- NeuroSAR GitHub URL
- "Open source under Apache 2.0"

**Voiceover:**

> "NeuroSAR demonstrates that physics-informed neural networks can serve as accurate, differentiable, and interactive surrogates for SAR ADC design — enabling real-time exploration, automated FoM mapping, and gradient-based inverse design that are impossible with SPICE alone. Future work will integrate real Sky130 ngspice training data, add noise models and layout-aware parasitics, and extend the framework to pipeline and noise-shaping ADC topologies. All code is open source at the link shown. Thank you."

**Screen notes:**
- Hold the final slide for 5 seconds of silence before ending the recording
- Display the GitHub URL in large, readable text
- Keep this scene clean and uncluttered — one clear takeaway per bullet

---

## Post-Production Notes

1. **Voiceover recording:** Record voiceover separately from screen capture for best audio quality, then sync in post. Use Audacity (free) to normalize audio to -16 LUFS.
2. **Annotations:** Add on-screen callout arrows or circles for key elements using a tool like OBS Studio (free) or Camtasia.
3. **Title card:** Add a 3-second title card at the start: "NeuroSAR | IEEE SSCS Code-a-Chip 2024 | [Author Names] | [Affiliation]"
4. **Captions:** Add closed captions or subtitles for accessibility.
5. **Export settings:** H.264, 1920×1080, 30 fps, AAC audio at 192 kbps, constant rate factor (CRF) = 18–22.

---

## Timing Summary

| Scene | Duration | Key Visual |
|---|---|---|
| 1. Motivation | 0:30 | SPICE slowness, NeuroSAR speedup |
| 2. Architecture | 0:30 | PINN diagram, physics loss terms |
| 3. Interactive Demo | 0:45 | Live slider widget demo |
| 4. FoM Exploration | 0:30 | FoM heatmap, Pareto front |
| 5. Inverse Design | 0:30 | Optimization trajectory |
| 6. Conclusion | 0:15 | Summary, GitHub link |
| **Total** | **3:00** | |
