---
name: generate-requirements-ledger
description: 从芯片需求输入中穷举、原子化并建立带原文证据的 requirements.ledger.json。用于详细设计和 CSIR 生成之前的需求盘点；不负责生成详细设计或 CSIR，也不负责填写 represented/contracted/question/unsupported 审查状态。
---

# Generate Requirements Ledger

建立一份可由独立 Reviewer 审计的需求全集，而不是撰写摘要。详细字段见
[ledger-contract.md](references/ledger-contract.md)，生成 ledger 前必须读取。

## 边界

- 只提取源文档明确表达的需求、目标、约束、假设、定义和集成义务；不得补写“常见设计”。
- 不生成或修复 CSIR；完成 ledger 后再使用 `generate-csir-draft`。
- 不生成详细设计文档；ledger 完成后由 Author 先生成详细设计，再生成 CSIR。
- 不判断需求是否已被 CSIR 表征，所有新条目的 `status` 都必须为 `null`。
- 输入已是详细设计文档时，输出 `document_kind=detailed_design` 的分类证据，不创建 ledger。
- 混合文档只要仍包含目标级、未落实为设计决策的规范性内容，就按 `requirements` 处理。

## 初次生成

1. 给源文档建立稳定 block inventory。标题、正文、表格行、图注、脚注、列表项和数值约束
   都要有 locator；不要只读取正文段落。
2. 对每个 block 做 disposition：
   - `mapped`：列出一个或多个 requirement ID；
   - `excluded`：给出具体排除理由；
   - 不允许留下 `unexamined`。
3. 将规范性内容拆成可独立实现、验证或决策的原子条目。一个句子同时约束接口、时序和异常
   行为时应拆成多个条目，并都保留同一原文 evidence。
4. 使用基于 source digest、locator 和规范化 claim 的稳定 ID；不得使用会因插入漏项而整体
   重编号的顺序号。
5. 保留原文摘录与精确 locator。概括文字不能取代原文 evidence，无法定位的条目不得发布。
6. 做反向覆盖审计：每个 ledger 条目能回到 source；每个 source block 都 mapped 或 excluded；
   接口、寄存器、状态、流水线/并发、时钟复位、时序、异常、边界、软件可见行为、IP 集成、
   PPA/物理目标等类别逐类检查。类别检查只用于发现遗漏，不能凭空生成需求。
7. 发布前确认所有条目 `status=null`，并输出 extraction summary：各类计数、排除计数、尚无法
   解析的 source block。存在无法读取的 block 时失败，不得假装完成。

Reviewer 判定失败时，Author 可以依据 source 和 review feedback 修订现有 ledger 的结构、文本和
evidence；同一 ID 的条目如果保留，其 `status` 不得改变，新增条目的 `status` 必须为 `null`。
随后同步修订详细设计和 CSIR，并发布新的 Artifact；旧 Artifact 保留。删除或改 ID 的语义是否
合理不由本 Skill 宣布，必须交给下一轮 Reviewer 对照原始 source 重新判断。
