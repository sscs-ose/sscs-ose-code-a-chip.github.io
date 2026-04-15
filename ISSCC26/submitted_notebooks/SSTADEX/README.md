# SSTADEX - Structured and Systematic Analog Design Exploration

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

SSTADEX is a structured workflow for analog design exploration based on symbolic analysis, lookup-table-driven device characterization, reusable primitive abstractions, and hierarchical macromodel composition.

This submission presents the methodology through progressively more complex examples, starting from transistor lookup-table generation and primitive construction, and culminating in the design exploration of a one-stage OTA and a two-stage OTA.

>Recommended usage for this submission is through Google Colab, since the notebook was designed and validated for that environment.

## Contents

This submission includes:

- Background material on the SSTADEX methodology
- LUT generation and device characterization workflow
- Primitive-level modeling examples
- One-stage OTA design exploration
- Two-stage OTA hierarchical design exploration

## Scope

The main contribution of this submission is the Python library SSTADEX, a reusable framework for structured analog design exploration. While our previous publication introduced the methodology, the library presented here was developed afterwards as a more complete software implementation, enabling symbolic analysis, lookup-table-based primitive modeling, hierarchical macromodel construction, and condition-driven exploration workflows.

The accompanying notebook demonstrates how the library can be used in practice through representative examples, culminating in the design exploration of one-stage and two-stage OTAs.

## Dependencies

The flow relies on Python-based exploration scripts together with symbolic analysis and SPICE-based characterization.

Part of the LUT generation stage reuses and adapts code from *Mosplot: The MOSFET Characterization Tool* by Mohamed Watfa (GitHub repository, March 2025, accessed March 31, 2025: https://github.com/medwatt/gmid).