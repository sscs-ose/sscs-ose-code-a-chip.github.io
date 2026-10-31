# Physical closure workflow

## 执行顺序

1. 读取 immutable netlist、implementation constraints、PDK/macro dependency lock，记录摘要并按
   用途验证视图：所有实际放置的 master 需要 LEF；参与功能或时序分析的 standard cell、memory
   macro 以及带信号/timing pin 的单元需要适用的 Liberty；stream-out 前再核对实际 ODB master
   的 GDS。没有信号 pin、不会进入 STA 的纯物理 tap/fill/endcap/decap 不要求 Liberty，不能因其
   只有 LEF/GDS 就阻断 PnR。
   不要要求整份 LEF catalog 的所有可选 abstract master 都存在于 GDS；未被引用的 LEF-only
   master 不阻断流程。被引用 master 的阶段必需视图缺失或错误时报告
   `Error-Class: invalid_physical_view` 并停止。LVS/CDL/SPICE 缺失应记录为后续 signoff gap，
   但不能单独作为 placement、CTS、routing、STA 或 GDS stream-out 的停止条件。
2. 固定 top、corner、clock/IO constraints、die/core、utilization、macro placement 和工具版本；不要用
   改约束来消除违规。
3. 按 ORFS 正常顺序完成 floorplan、placement、CTS 和 pre-route repair。
4. 执行 global route、detailed route 与天线修复。此后才能放置 filler/decap，再做最终寄生提取。
5. 若最终 extraction 才出现 slew/capacitance 违规，将相同对象的 pre-route estimate 和 post-route
   值组成 `rc-comparison.json`，使用 Skill 脚本计算有界 margin。最多做两轮有证据的 ECO；每轮
   都重新完成 global route → detailed route/antenna repair → filler → extraction。
6. 从最终 ODB 导出两类用途明确的网表：
   - STA 网表保留所有具有信号 pin 或 Liberty model 的实例，包括天线二极管；
   - LVS 网表可以依据 LVS deck 另行处理物理单元，但不得冒充 STA 网表。
7. 独立加载最终 STA netlist、SPEF、SDC 和与 ODB 相同的 Liberty 集合。任何 missing
   instance/net/pin binding 都是失败；比较同一批路径及 setup/hold，不能只比较格式化后的零。
8. 重新检查 detailed-route DRC、连通性、天线、setup/hold、slew、capacitance、fanout 和宏保留，
   并以最终 ODB 的实际实例集合核对每一个 master 都能在 stream-out GDS 中解析。
9. 写一致性报告并等待平台 Gate。Gate 通过前不得发布 layout/physical.implementation。

## 滚动 ODB checkpoint 契约

物理收敛期间始终只维护两个槽位：

- `build/pnr/checkpoints/slot-a.odb`
- `build/pnr/checkpoints/slot-b.odb`

选择修改时间更老（或尚不存在）的槽位。先写入同目录临时文件，确认 OpenROAD `write_db` 成功且
文件非空后再原子替换目标槽位；旧槽位在新文件完整落盘前不得删除。随后原子更新
`build/pnr/checkpoints/latest.json`，至少包含 `schema_version`、`active_slot`、`stage`、
`created_at`、`tool_version`、输入 Artifact/commit 摘要、DRC/antenna/setup/hold 等当前可得指标，
以及从该 ODB 继续执行的命令和脚本入口。不得生成无限增长的 `checkpoint-001...` 文件。

以下事件属于重大进展，必须保存：placement 完成、CTS 完成、global route 完成、首次 detailed
route 完成、天线二极管插入并合法化、一次 ECO 让 DRC/天线/时序指标实质改善、最终导出完成。
此外，启动任何预计可能接近 Run 剩余时间的单条 OpenROAD/ORFS 命令前，先保存当前 ODB。
checkpoint 是恢复点，不是通过证据；只有最终检查和 Gate 能把执行状态置为 `succeeded`。

## RC comparison contract

`derive_rc_guardband.py` 输入：

```json
{
  "schema_version": 1,
  "slew_ratios": [1.18, 1.31],
  "capacitance_ratios": [1.12, 1.27],
  "policy": {
    "percentile": 0.95,
    "safety_percent": 3,
    "min_percent": 0,
    "max_percent": 35
  }
}
```

每个 ratio 必须是同一对象、同一 corner 下的 `post-route / pre-route`，且为正有限数。没有可比
样本时停止并报告证据不足，不猜 guardband。输出中的 margin 是百分数，供 ORFS
`SLEW_MARGIN` / `CAP_MARGIN` 使用。

## Post-route export consistency contract

写入 `reports/pnr/post_route_export_consistency.json`：

```json
{
  "schema_version": 1,
  "status": "passed",
  "database_odb": "build/pnr/results/6_final.odb",
  "sta_netlist": "build/pnr/results/6_final.sta.v",
  "spef": "build/pnr/results/6_final.spef",
  "sdc": "build/pnr/results/6_final.sdc",
  "missing_spef_binding_count": 0,
  "database_hold_slack_ns": 0.006321166,
  "sta_hold_slack_ns": 0.006321166,
  "path_slack_max_abs_delta_ns": 0.0,
  "timing_instances": {"database": 12345, "sta_netlist": 12345},
  "antenna_instances": {"database": 99, "sta_netlist": 99},
  "evidence": [
    "reports/pnr/export_sta_netlist.log",
    "reports/pnr/netlist_spef_with_diodes.log"
  ]
}
```

所有路径相对 Task workspace，必须存在且非空。数字来自未截断的工具输出；若没有天线实例，
两个 antenna count 都写 0。`status=passed` 仅在以下条件全部成立时合法：

- missing SPEF binding 为 0；
- ODB 和 STA 网表的 timing/antenna instance 数量分别相等；
- hold slack 差和所检查路径的最大 slack 差均不超过 Gate tolerance；
- 证据日志存在且绑定本轮输入和工具版本。

## 错误分类和停止条件

- `invalid_physical_view`：当前 PnR/STA/stream-out 必需的冻结 PDK/macro view 缺失、不一致或本身
  违反工艺检查；立即停止，不重试。仅缺 LVS/CDL/SPICE 时记录后续 signoff gap，不使用此分类。
- `post_route_export_mismatch`：ODB、STA netlist、SPEF 不一致；保留当前 WIP，由同一 pnr-engineer
  修复导出和重新复核，最多使用 Role 预算内的一次返工。
- `transient_error`：工具进程或基础设施瞬态失败，未得到工程结论。
- `unknown`：其余失败；不要无边界重复昂贵 PnR。

两轮 RC ECO 后仍不能满足冻结最终门限时，以真实 failed 证据结束；不得继续增大 guardband、
降低频率、换 corner 或隐藏违规。
