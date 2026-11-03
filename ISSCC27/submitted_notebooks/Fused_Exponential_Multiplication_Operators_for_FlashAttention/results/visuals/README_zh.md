# 可视化结果索引

[English](README_en.md) | **中文**

四个 `fa_lane` 设计（FP32/BF16 × baseline/ExpMul）在 nangate45 上跑完 ORFS 全流程后的
所有图像与版图。

## 目录

```
visuals/
├── layout_compare.png          四个设计 post-route 版图 2×2 对比（含面积/功耗标注）
├── stages_fp32_base.png        FP32 baseline 的 placement / congestion / IR-drop / routing
├── stages_fp32_exp.png         FP32 ExpMul 同上四个阶段
├── orfs_visuals.tgz            原始 ORFS 报告包（本地副本，未入库）
├── gds/                        四个设计的 6_final.gds（KLayout 可直接打开）
│   ├── fa_lane_b_top/base/6_final.gds       FP32 baseline  16.1 MB
│   ├── fa_lane_e_top/base/6_final.gds       FP32 ExpMul     6.8 MB
│   ├── fa_bf16_b_top/base/6_final.gds       BF16 baseline   5.6 MB
│   └── fa_bf16_e_top/base/6_final.gds       BF16 ExpMul      3.5 MB
└── fa_lane_b_top/ fa_lane_e_top/ fa_bf16_b_top/ fa_bf16_e_top/
    └── base/*.webp.png        ORFS 原始阶段图（每设计 10 张）
```

每个设计目录下的 10 张图：

| 文件 | 内容 |
|---|---|
| `final_all.webp.png` | 完整版图（routing + placement + pin） |
| `final_routing.webp.png` | 布线结果 |
| `final_placement.webp.png` | 布局（标准单元分布） |
| `final_congestion.webp.png` | 全局布线拥塞热图 |
| `final_ir_drop.webp.png` | 电源 IR drop 热图 |
| `final_clocks.webp.png` / `cts_default_clk*.png` | 时钟树 |
| `final_worst_path.webp.png` | 关键路径 |
| `final_resizer.webp.png` | resize 后的布局 |

## 面积/功耗对照

| 设计 | 面积 (µm²) | 功耗 @50 MHz |
|---|---|---|
| FP32 baseline | 30 539 | 3.42 mW |
| FP32 ExpMul | 9 362（−69.3%） | 1.02 mW（−70.2%） |
| BF16 baseline | 9 041 | 0.931 mW |
| BF16 ExpMul | 5 092（−43.7%） | 0.554 mW（−40.5%） |

> 版图对比里能直接看出：FP32 baseline 的布局最满（30.5k µm²），ExpMul 版明显稀疏；
> BF16 两版都更紧凑。功耗数字来自门级 VCD + SPEF（`results/phase4/power_*.log`）。
