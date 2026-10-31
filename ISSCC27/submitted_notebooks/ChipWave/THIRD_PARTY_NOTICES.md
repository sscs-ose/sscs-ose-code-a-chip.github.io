# ChipWave naming notice

ChipWave is the public submission name. Upstream attributions and original
license identities below retain their recorded names; renaming the submission
does not change ownership or licensing.

# Third-party notices and release scope

Original submission material and the selected ChipNebula runtime distribution
use the root Apache-2.0 license. Original third-party copyrights and licenses
remain applicable. The upstream private ChipNebula repository's global
Proprietary designation is unchanged.

| Material used | Origin and attribution | License / record |
|---|---|---|
| Used ChipNebula CLI, TaskGraph, adapter, IP and physical dependencies | ChipNebula contributors, `mvp_test` revision `993905bb64a3320a8e4fa31c6768948b8b20fca2`; selected component release requested by the project owner | `runtime/LICENSE`; `runtime/used-components.json` |
| T09 contract, evaluator, program images and stored oracle traces | DigitalICDesignBenchmarK contributors; revision `75997d1d39cce5a4c23c6a08e41d710ffd891399`; original RISC-V test attributions retained in the bundled files | `verification/benchmark/LICENSE`; `verification/benchmark/source-manifest.json` |
| `gemm_pe.sv` | Model2GDS, Yixuan Zhuang; revision `573b4f880c252d2b5900309d4de637dc6a861979`; reused unchanged with a separately authored adapter | `ip/model2gds-dot4/LICENSE.model2gds`; `ip/model2gds-dot4/provenance.json` |
| ORFS flow scripts and utilities | The OpenROAD-flow-scripts contributors; build/run script copyright (c) 2018–2023, The Regents of the University of California; revision `3a964e13f11a4e435aac01ffa14db0a7d2853720` | BSD-3-Clause in `toolchain/orfs/LICENSE_BUILD_RUN_SCRIPTS`; exact copied hashes in `toolchain/orfs/source-manifest.json` |
| Sky130HD standard-cell process material | SkyWater PDK authors and the contributing open_pdks community; cell geometry is included in the composed final layout and the used ORFS platform snapshot | Apache-2.0; `toolchain/licenses/Apache-2.0.txt`; original cell/library notices retained in the copied platform files |
| Sky130 KLayout DRC runset | `toolchain/orfs/flow/platforms/sky130hd/drc/sky130hd.lydrc`, obtained with the pinned ORFS snapshot; original header declares GNU GPLv3 | GPLv3; full text in `toolchain/licenses/GPL-3.0.txt`. This separately distributed script is not relicensed under the root Apache-2.0 license. |
| OpenROAD | The OpenROAD Authors, copyright (c) 2018–2025; binary revision `4a7cf9b22a5f24f32ce4f4eb1448fef4d2a367ca` | `toolchain/licenses/OpenROAD.BSD-3-Clause.txt` |

The EDA executables are external prerequisites; source/install references and
recorded versions accompany the case. Python dependencies are installed from
the pinned requirements rather than copied from a private environment. They
retain their upstream licenses.

The notebook and figures attribute reused code and tools in the References
section. GDS images are renderings of actual layout data. Composed layouts
contain upstream standard-cell material and preserve that material's licensing;
the root license does not replace third-party terms. No account credentials,
model authentication files or unrelated private project source is included in
the release.
