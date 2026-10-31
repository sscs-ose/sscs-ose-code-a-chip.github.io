# Reference map

What each source cited in the notebook supports, at which strength, and what it does not support. Bibliographic data
are in `references.bib`. Domain transfers (systems engineering, design-process, organization research applied to analog
design) are the notebook's Interpretation or Reflection, not claims of the source.

| Key | Type | Supports in the notebook | Does not support |
|---|---|---|---|
| `Razavi2017AnalogCMOS` | canonical textbook | standard results of Section 1 (switch on-resistance, follower error, feedback, headroom); trade-offs in 3.4 | any design methodology |
| `Gray2009AnalogIC` | canonical textbook | same as Razavi, independently; differential rejection and its matching cost (3.4) | — |
| `CarusoneJohnsMartin2012AnalogIC` | canonical textbook | sampled-data mechanisms: charge injection, kT/C, sampled noise as the variance of the track-mode voltage (1, 3.4, 3.5) | — |
| `Black1934Feedback` | seminal paper | negative feedback reduces sensitivity to open-loop quantities at a loop-gain/stability cost (3.4) | — |
| `WegmannVittozRahali1987ChargeInjection` | primary paper | channel-charge split depends on terminal impedances and gate-edge rate (3.1) | the size of the split in this circuit |
| `EichenbergerGuggenbuhl1990Dummy` | primary paper | dummy-switch compensation and its 50/50 split assumption (3.4) | — |
| `AboGray1999Bootstrap` | primary paper | bootstrapped sampling switch (3.4) | — |
| `Razavi2015Bootstrapped` | tutorial article | bootstrapped switch operation (3.4) | — |
| `IEEE2011Std1241` | standard | terminal-based offset/gain separation in ADC testing, used by analogy for the held-sample metric (3.5) | that the held-sample residual is INL in the standard's sense |
| `NASA2016SEHandbook` | official handbook | requirement hierarchies and allocations (1, 3.1) | analog design practice (transfer is Interpretation) |
| `KundertEtAl2000MixedSignalSoC` | peer-reviewed paper | top-down allocation and refinement in mixed-signal design; integration exposing effects a block test omits (1, 3.1, 3.3) | — |
| `Kundert2003TopDown` | practitioner article | same, in practice (3.3) | — |
| `ChangKundert2007Verification` | peer-reviewed paper | verification models must keep the effects relevant to the question (3.3) | — |
| `RutenbarGielenRoychowdhury2007Hierarchical` | review paper | hierarchical specification translation informed by lower-level capability; multi-objective exploration (1, 3.1) | — |
| `MukherjeeCarleyRutenbar2000OperatingRange` | peer-reviewed paper | designing over an operating range; numerical optimization of analog circuits (1, 3.2) | — |
| `Graeb2007DesignCentering` | monograph | variation-aware design, sensitivity analysis, design centering (1, 3.2) | — |
| `McConaghyEtAl2013VariationAware` | practitioner monograph | corners represent global variation and do not cover mismatch (3.5) | — |
| `Simon1962Architecture` | seminal paper | near-decomposability as the basis of hierarchy (1) | analog specifics (transfer is Interpretation) |
| `Steward1981DSM` | seminal paper | coupled design parameters forming cycles that no sequential order resolves (1) | that the S&H network has this structure (Interpretation) |
| `SmithEppinger1997Iteration` | peer-reviewed paper | coupled design tasks converge by iteration (1) | analog specifics |
| `KeatingBricaud2002Reuse` | book | reuse delivers specifications, models and verification material with the design (3.6) | — |
| `Conway1968Committees` | seminal article | organization structure mirrors system structure (3.6) | analog consequences (Reflection) |
| `MacCormackBaldwinRusnak2012Mirroring` | empirical paper | mirroring in product development (3.6) | analog consequences (Reflection) |
| `SkyWater2020SKY130PDK` | official PDK documentation | SKY130 1.8 V device model validity to 1.95 V; standard-cell characterization supplies (3.5) | silicon behaviour of this circuit |
| `Ngspice42Manual` | official manual | simulator options and integration methods (3.5) | — |
| `ChenEtAl2024Artisan` | peer-reviewed (DAC 2024) | LLM-based op-amp design on a benchmark (4) | general analog design capability |
| `AhmadzadehEtAl2026AnaCraft` | peer-reviewed (TCAD 2026) | PVT-aware sizing with model-based RL (4) | verification planning or evidence judgment |
| `ShenEtAl2026Atelier` | peer-reviewed (TCAD 2026) | multi-agent analog analysis/design with tool use (4) | — |
| `LiuEtAl2025LayoutCopilot` | peer-reviewed (TCAD 2025) | interactive analog layout through tool calls (4) | — |
| `Yoshioka2026VibeTapeout` | preprint (arXiv, not peer-reviewed) | a long-horizon SKY130 agent flow with reported false passes (4) | general reliability of agent flows |
