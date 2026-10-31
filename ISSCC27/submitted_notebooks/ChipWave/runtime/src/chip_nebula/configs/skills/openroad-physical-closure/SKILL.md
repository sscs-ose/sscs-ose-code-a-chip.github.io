---
name: openroad-physical-closure
description: 用 OpenROAD/ORFS 完成布局布线后的电气收敛、RC guardband、天线修复以及 ODB、STA 网表与 SPEF 一致性检查。用于 pnr-engineer 执行或返工 physical implementation；不用于修改 RTL、综合输入、冻结约束或 PDK/macro views。
---

# OpenROAD Physical Closure

目标是发布一组彼此一致、可独立复核的 post-route 产物，而不是让单次 OpenROAD 命令返回零。
执行 PnR 或修复最终 slew/capacitance、天线、SPEF 绑定问题前，必须读取
[closure-workflow.md](references/closure-workflow.md)。

## 不可跨越的边界

- 冻结 netlist、implementation constraints、PDK 和 macro views 都是只读输入；它们有问题时
  以正确 Error-Class 停止，不在 PnR 工作区内替换。
- 固定阶段顺序为 global route → detailed route/antenna repair → filler placement → extraction。
- RC guardband 只允许收紧 pre-route repair 目标，不能放宽最终 Liberty、STA、DRC 或天线门限。
- 最终 STA 网表必须保留所有带信号 pin 或 Liberty timing model 的实例；不能因为 master 类型是
  `CORE_ANTENNACELL` 就删除天线二极管。
- 不得把 ODB 内部 STA 当作唯一证据。必须另外用导出的 netlist、SPEF、SDC 和同一组 Liberty
  跑一次 STA，并生成 `reports/pnr/post_route_export_consistency.json`。
- 只有 `post-route-export-consistency` Gate 与其余物理检查全部通过，才能把
  `reports/pnr/execution_status.json` 写成 `succeeded`。
- 长流程不能只依赖 ORFS 最终产物。按 workflow reference 的滚动 checkpoint 契约保存两个 ODB
  槽位；取得重大进展或启动预计耗时较长的下一步之前先落盘，避免 Run 超时丢失数小时收敛工作。

## 可复用工具

RC 偏差已经整理为逐样本 `post/pre` 比值时，运行：

```sh
python .codex/skills/openroad-physical-closure/scripts/derive_rc_guardband.py \
  --input reports/pnr/rc-comparison.json \
  --output reports/pnr/guardband.json
```

Claude Code 工程使用同一脚本的 `.claude/skills/...` 副本。脚本只计算有界建议，不修改流程；
根据输出设置 ORFS `SLEW_MARGIN` / `CAP_MARGIN` 后，仍须按完整阶段顺序重跑受影响部分。

出口报告结构、停止条件和错误分类见 workflow reference。不要自行发明另一个“通过”格式。
