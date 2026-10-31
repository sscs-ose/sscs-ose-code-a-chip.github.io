# FoldAgent：命名与提交前核查

本版定位：**有明确设计取舍、可复核的工程教学案例**。核心问题是：在本案例的固定投影面积、增加一层逻辑硅面积的条件下，保持原有服务周期会带来哪些接口与物理实现代价？

| 论点环节 | 对应实现与已有证据 | 结论范围 |
|---|---|---|
| 保留服务安排 | 32 个并行 INT8 乘法、352 B 有效数据存储、原有周期安排 | 所选切分保持原有资源与周期约定 |
| 付出通信代价 | 725 条功能连接，其中 179 条为 host 穿越；同周期组合返回 | 接口容量和跨层往返是具体设计义务 |
| 检查已实现电路 | 162 组配对场景、冻结两层物理证据、三组联合 STA | 在当前工作负载、TT 与假定垂直 RC 条件下成立 |
| 用预算练习做选择 | 原计算单元比较 10/12.5 µm 和八/四个移动通道 | 四通道为解析示例，后续需要实现与性能测量 |

## 本轮评审处理

| 建议 | 修改 | 状态 |
|---|---|---|
| 完成公开授权与开放许可 | A–F 分项清单覆盖正文、RTL、验证、物理成果、数据及工具补丁；整理可转交的回复模板 | 2026-10-31 作者确认可以公开；项目 Apache-2.0、补丁 BSD-3-Clause 及第三方声明已落实 |
| 开篇突出取舍 | 压缩摘要，首段直接连接固定投影面积、增加逻辑硅面积、162 组吞吐、725 条连接与同周期往返 | 已修改；保留案例约束、TT 和假定互连模型 |
| 让读者做一次设计判断 | 计算前先预测；计算后展开解释接口容量、算术资源及吞吐验证；原函数和代码单元保持一致 | 已修改；四通道只作为解析预算示例 |
| 给图片明确任务 | 保留现有 GDS 图，补上原 placement 图入口；区分 200 × 200 µm 跨层窗口与 2.8 µm M4 接入窗口；串起图 4、4b、2B 和图 6 | 已修改；图像与源数据复用 |

## 沿用的结果

- v4：独立解压和 Python 环境中的 324 次 RTL 仿真、三组联合 STA，结果匹配归档记录；同一主机与已记录工具。
- v5：控制层 GDS 复用、计算层由冻结 DEF 格式导出，以及单元/引脚读回检查。
- v6：文稿、现有 Notebook 单元、链接及打包校验；新增设计实验为零。

公平物理基线、最终 ECO 成本、能耗、PVT 和独立 GDS DRC/LVS 保持为后续研究。本轮按现有证据完成表达，不新增实验。

## v7 作者与许可更新

作者顺序为 Zhanchen Zhao、Wenyu Sun、Yaqing Lai、Yubo Deng，所有作者单位均为 Tsinghua University。赴会代表为 Zhanchen Zhao。已更新根许可证、署名声明、适用范围、中英文稿与作者元数据；文中技术论点沿用 v6。

## v8 命名与流程表达

按作者选择更名为 FoldAgent，Notebook 和中英文 HTML 使用同名入口。第 3 节按现有记录交代规划 agent、RTL 实现、自动化检查与工程反馈；既有设计取舍、测量结论和适用条件保持一致。旧平台及文件名保留在原始来源记录中。

## v9 submission review

- Section 3 now links the historical session record, task intent, nine frozen planning briefs, model/attempt configuration, implementation note and exact RTL delivery. The [agent evidence guide](evidence/agent/README.md) records generation replay scope and the two local RTL revisions within the saved workflow attempt.
- The submission contains only package-manifest.json entries plus the manifest. Validation work copies, runtime caches and browser previews stay in the author workspace; compact reports and the test log are retained.
- The English and Chinese design-exercise explanations are ordinary visible sections. Print styles hide only code/output disclosures, preserving the interface-capacity, compute-resource and throughput explanations.
- Validation reran the seven existing notebook cells and eight lightweight checks. Prior RTL simulations, STA, physical results and all figures are reused; no new design experiments or model calls were added.
