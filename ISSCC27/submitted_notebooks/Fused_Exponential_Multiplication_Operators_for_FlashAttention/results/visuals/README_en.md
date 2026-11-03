# Visual results — index

**English** | [中文](README_zh.md)

All images and layouts produced by the complete ORFS flow for the four `fa_lane` designs
(FP32/BF16 × baseline/ExpMul) on nangate45.

## Contents

```
visuals/
├── layout_compare.png          post-route layouts of the four designs, 2×2, annotated
├── stages_fp32_base.png        FP32 baseline: placement / congestion / IR-drop / routing
├── stages_fp32_exp.png         FP32 ExpMul: same four stages
├── orfs_visuals.tgz            raw ORFS report bundle (local copy, not committed)
├── gds/                        the four 6_final.gds files (open with KLayout)
│   ├── fa_lane_b_top/base/6_final.gds       FP32 baseline  16.1 MB
│   ├── fa_lane_e_top/base/6_final.gds       FP32 ExpMul     6.8 MB
│   ├── fa_bf16_b_top/base/6_final.gds       BF16 baseline   5.6 MB
│   └── fa_bf16_e_top/base/6_final.gds       BF16 ExpMul      3.5 MB
└── fa_lane_b_top/ fa_lane_e_top/ fa_bf16_b_top/ fa_bf16_e_top/
    └── base/*.webp.png        original ORFS stage images (10 per design)
```

The ten images in each design directory:

| File | Contents |
|---|---|
| `final_all.webp.png` | complete layout (routing + placement + pins) |
| `final_routing.webp.png` | routed layout |
| `final_placement.webp.png` | standard-cell placement |
| `final_congestion.webp.png` | global-route congestion heat map |
| `final_ir_drop.webp.png` | power-grid IR-drop heat map |
| `final_clocks.webp.png`, `cts_default_clk*.png` | clock tree |
| `final_worst_path.webp.png` | critical path |
| `final_resizer.webp.png` | layout after resizing |

## Area and power

| Design | Area (µm²) | Power @ 50 MHz |
|---|---|---|
| FP32 baseline | 30 539 | 3.42 mW |
| FP32 ExpMul | 9 362 (−69.3 %) | 1.02 mW (−70.2 %) |
| BF16 baseline | 9 041 | 0.931 mW |
| BF16 ExpMul | 5 092 (−43.7 %) | 0.554 mW (−40.5 %) |

> The layout comparison shows the difference directly: the FP32 baseline (30.5k µm²) is the
> densest, the FP32 ExpMul version (9.4k µm²) is visibly sparser, and both BF16 versions are more
> compact. The power figures come from gate-level VCD activity plus SPEF
> (`results/phase4/power_*.log`).
