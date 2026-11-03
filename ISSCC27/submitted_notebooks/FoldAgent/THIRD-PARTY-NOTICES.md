# Source and license notices

Project-owned materials are released under Apache-2.0 following the author's confirmation on 31 October 2026. The scope is in [LICENSE-SCOPE.md](LICENSE-SCOPE.md); this file preserves the applicable upstream terms and attribution.

| Material | Origin and applicable terms |
|---|---|
| Project RTL, verification, reports/data, physical design and manuscript | FoldAgent contributors; Apache-2.0. Exact source identities remain in sources.json. |
| reproduction/original/logic_folding_performance.py and reproduction/performance.py | Chip Nebula Team platform, local commit c354925a32c8b90056d88f227e30cce474ade59a. The packaged original excerpt and portable adaptation are authorized for Apache-2.0 release. The adaptation replaces execution/logging helpers; reproduction/README.md describes the preserved measurement functions. The original platform's Proprietary metadata is retained as a historical source record in licenses/ChipNebula-original-project.toml. |
| evidence/agent/ | Bounded project experiment recipe, task intent, frozen briefs and implementation note; Apache-2.0. Exact source/snapshot/commit identities are in evidence/agent/provenance.json. The complete external orchestration platform and model service retain their own terms. |
| physical/tool-patches/*.patch | Modifications to OpenROAD 4a7cf9b22a5f24f32ce4f4eb1448fef4d2a367ca. Copyright (c) 2018-2025, The OpenROAD Authors. BSD-3-Clause text is retained in licenses/OpenROAD-BSD-3-Clause.txt and physical/tool-patches/LICENSE; the adjacent NOTICE identifies the project modifications. |
| physical/gds/*.gds, embedded standard-cell geometry | SKY130 HD library geometry retains Apache-2.0. The upstream text is in licenses/SKY130-HD-Apache-2.0.txt and source hashes are in physical/gds/inputs.json. Project placement/routing contributions use Apache-2.0. |
| physical/gds/export-technology.lyt | Technology metadata from the installed ORFS revision 3a964e13f11a4e435aac01ffa14db0a7d2853720; original SKY130 layer information retained, with local LEF-path changes recorded in inputs.json. ORFS build/run-script BSD-3-Clause notices (The Regents of the University of California) are retained in licenses/ORFS-BSD-3-Clause.txt alongside the SKY130 Apache-2.0 notices. |
| OpenSTA dependency | Parallax Software; GPL-3.0-or-later. Existing license text is in licenses/OpenSTA-GPL-3.0.txt. Obtain tool binaries/source separately. |
| Icarus Verilog dependency | Stephen Williams and contributors; GPL-2.0-or-later. Existing text is in licenses/Icarus-GPL-2.0.txt. Obtain tool binaries/source separately. |
| SKY130 HD Liberty dependency | Obtain the fixed public version in DEPENDENCIES.md under its existing Apache-2.0 terms. Selected file SHA-256 remains recorded. |

Upstream references: [SKY130 HD license](https://github.com/google/skywater-pdk-libs-sky130_fd_sc_hd/blob/ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1/LICENSE), [ORFS build/run license at the installed revision](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/3a964e13f11a4e435aac01ffa14db0a7d2853720/LICENSE_BUILD_RUN_SCRIPTS), [ORFS SKY130 technology source](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/3a964e13f11a4e435aac01ffa14db0a7d2853720/flow/platforms/sky130hd/sky130hd.lyt), and [OpenROAD license at the patch base](https://github.com/The-OpenROAD-Project/OpenROAD/blob/4a7cf9b22a5f24f32ce4f4eb1448fef4d2a367ca/LICENSE).

The complete upstream platform repository retains its existing license. This authorization covers the bounded project materials in this package. KLayout was used for export/rendering; no tool binary is redistributed. Original records retain AI-assistance disclosures and source hashes.
