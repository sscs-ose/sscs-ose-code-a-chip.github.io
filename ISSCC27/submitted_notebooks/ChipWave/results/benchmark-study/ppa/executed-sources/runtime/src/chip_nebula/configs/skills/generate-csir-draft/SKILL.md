---
name: generate-csir-draft
description: 从芯片需求文档提取并生成 Compact SpecIR（.specir）draft，以及配套的 provenance.json / contracts.json sidecar。当用户要求把需求文档/spec/规格转换成 SpecIR、生成或修订 .specir draft、做需求到语义节点的追踪映射时使用。evidence-first、显式 hole/conflict、禁止猜测默认值，并通过 specir CLI 的 check/build 反馈循环保证 draft 可被确定性编译器接受。
---

# Generate CSIR Draft

从自然语言需求文档生成 **Compact SpecIR v0.1** draft（`.specir` + `provenance.json` + `contracts.json`）。

语言规范：`docs/CSIR_v0.1_Draft.md`；编译器实现：`docs/CSIR_v0.1_Implementation.md`；风格样例：`examples/csir/`。

**系统边界（必须遵守）**：编译器是确定性的，不调用 LLM。你的职责是上游 extraction/review Agent：把需求变成语法正确、语义诚实、带追踪的 draft；诊断、typecheck、signoff 判定全部交给 `specir` CLI。绝不要用"改编译器"或"忽略诊断"的方式让 draft 通过。

## 运行编译器

```sh
# 未安装包时：
PYTHONPATH=src python3 -m csir <command> ...
# 或安装后：
specir <command> ...
```

常用命令：

```sh
specir parse <file> [--fragment]            # source AST JSON
specir fmt <file> --check                   # canonical 格式校验
specir check <file> [--provenance p.json] [--contracts c.json] [--verbose] [--no-solver]
specir nodes <file>                         # stable semantic node ID 列表
specir init-provenance <file> -o provenance.json   # 带真实 node ID 的 sidecar 模板
specir build <file> --out build/<name> --signoff [--provenance p.json] [--contracts c.json]
specir emit-circt <file> -o design.mlir
```

退出码：`0` 成功；`1` semantic/signoff 失败；`2` parse/I/O 错误。无 Z3 时 choice 证明降级为 `W-CHOICE-NOT-PROVEN`，不假装证明成功。

## 工作流

### 1. 读需求，先做 scope gate

逐条判断需求是否**定义或约束芯片/DUT 的需求、目标、边界、可观察行为或详细设计**：

- 在范围内：分配 requirement ID（如 `REQ-12`），进入 ledger，可映射 node/contract。
- 不在范围内（教程、背景、人员/组织流程、平台提供方式、纯验收操作、重复已有约束）：不分配 ID、不映射；记入 extraction report 的 `excluded_source_context`（locator + 排除理由）。
- 判断依据是**约束对象**，不是章节标题。芯片级 PPA/STA target、工作条件、实现约束**在范围内**，但应走 contract sidecar（见第 4 步），不进 core IR。

### 2. 写 `.specir` —— encode behavior，不 encode label

Canonical Style（附录 A，必须遵守）：

- **行为优先，不写 ontology label**。不写 `predicate=set_wins` 之类；写成显式 next-state equation。禁止发明 `sticky` / `w1c` / `irq` / `dma` 等 keyword。
- **`case` vs `priority` 是语义区分，不是风格选择**：
  - spec **明确**说"优先 / 否则 / 若同时发生 X 胜出" → 用 `priority`（有序 first-match，overlap 合法）。
  - spec **没写**优先级 → 用 `case`（无序 guarded choice，guards 必须可证明互斥）。**绝不要**根据文档行文顺序把 `case` 擅自变成 `priority`。
- **未决定的东西一律写命名 hole `?name`**（如 `?reset_value`、`?max_latency`），等客户澄清；**显式 `none`** 表示设计者确认"不需要"。两者严格区分。禁止猜默认值把 hole 填掉。
- state 缺 next equation、`case`/`priority` 无 `else` 且未覆盖全空间 → 编译器按 implicit hole 处理；宁可显式写出 `?name`。
- 不推断 hold、不推断 reset：state 不写 next 不是 hold；不写 reset intent 不是 `none`。
- 不把 extraction confidence 写进 `.specir`；LLM 审计信息只进 provenance sidecar。

核心语法速查（详见 Draft §3–§9，写之前对照 `examples/csir/`）：

```text
module NAME [(param...)] { ... }
in a, b: bit [@domain]                 # out / out state 同理
domain core = posedge clk, async reset !rst_n   # sync/async；无 reset 也可
state count: u8 @core reset 0          # reset 0 | reset none | reset ?name
out state irq: bit @core reset 0       # output + state 的 shorthand
const MASK: bits[8] = 8'hF0
param W: int = 32
let busy = s == BUSY                   # 纯组合本地命名，无存储
abstract result: bits[28]              # contract 约束的自由值，非 hole
abstract out score: bits[16]

irq' = priority { set -> 1; clear -> 0; else -> hold }   # 一行多语句才用分号
s' = case { s==IDLE && start -> BUSY; ... ; else -> hold }
busy = s == BUSY                       # 组合输出方程；组合环是 compile error

assume @core rose(req) |-> !req until ack unless reset
assert @core rose(req) |-> ##[1:4] ack unless reset
cover  @core rose(req) |=> ##2 ack
```

类型与表达式纪律（E-TYPE 家族，全部显式）：

- 类型：`bit` / `bits[N]` / `uN`、`u[W]` / `sN`、`s[W]` / `{A,B,C}`（enum）/ `int`（仅 param/width）。
- `bit` 用 `!` `&&` `||`；bitvector 用 `~` `&` `|` `^`。
- **无隐式位宽扩展/截断**：需要更宽结果必须显式 `zext(x,16)` / `sext(x,16)` / `trunc(x,8)` / `as_u(x)` / `as_s(x)`；signed/unsigned 混用必须显式 cast。
- enum 不参与算术；可显式 encode/cast 后运算。
- `hold` 只在 next-state equation RHS 的 choice branch / ternary context 中合法。
- 每个 state 恰好一个 next equation；`q'` 只能出现在 equation LHS。
- temporal bound 的 hole 写 `##[1:?max_latency]`——这是 signoff 阻断项，如实保留。
- 跨 domain 采样会产生 `E-CDC-UNQUALIFIED` diagnostic；保留它（这是 Spec review 价值），不要靠加同步器 keyword 掩盖——v0.1 核心 IR 没有 `sync2` 等概念。

### 3. 冲突处理（Provenance 层，不进 canonical IR）

两个来源矛盾时（如 `done` 是 pulse vs sticky）：

- **不要**用 confidence 0.51/0.49 决胜；**不要**把 conflict 写成可执行 value 混进 `.specir`。
- 在 provenance sidecar 的 `conflicts` 中记录（见下方 schema），canonical node 保持阻塞，向用户提出澄清问题。

### 4. 明确但不属于 core 的 obligation → contract sidecar

数值/统计/PPA/STA 等 core expression 与 temporal subset 表达不了的**明确**需求：

- 写成 `contracts.json`（schema 见下），并用 `apply CONTRACT_ID { role: expr }` 在 `.specir` 中做 typed named binding。
- `abstract` symbol 表示"需求已明确约束合法结果集合但不要求唯一实现函数"——**不是 hole**，不产生 `E-HOLE-UNRESOLVED`，但每个 abstract 必须至少被一个 `constrain` role 直接绑定（`y ^ y`、slice、`let` 间接引用都不算 coverage）。
- adapter 缺失（`status: adapter_required`）只是 verification readiness 问题，报 `N-CONTRACT-*`，不是客户需求缺失。
- 使用 contracts sidecar 时必须同时提供 provenance ledger，否则 checker 报错。

### 5. 用真实 node ID 填 provenance，跑反馈循环

node ID 由 canonical semantic content 生成，**不要手编**：

```sh
specir init-provenance draft.specir -o provenance.json   # 含全部真实 node_id 的模板
# 然后填入 requirements / evidence / extraction / conflicts
```

反馈循环（必须迭代到干净）：

```sh
specir fmt draft.specir --check
specir check draft.specir --provenance provenance.json --contracts contracts.json
# 修复由编码失误造成的 Error（含 E-PARSE）；根源在文档缺失/歧义的诊断（任何级别）原样保留、如实报告，别为了好看而掩饰
specir build draft.specir --out build/draft --signoff --provenance provenance.json --contracts contracts.json
```

常见诊断家族与正确响应（不要机械"修掉"，要修语义）：

| 家族 | 含义 | 响应 |
|------|------|------|
| `E-CHOICE-OVERLAP` | `case` guards 在 assumptions 下可重叠 | 回查 spec：有优先级依据→改 `priority`；无→向客户提问，或补 `assume` 排他性假设 |
| `E-CHOICE-COVERAGE` / hole | guard union 未覆盖全空间 | 补 `else`、或显式 `?name` hole 并提问 |
| `E-HOLE-*` | 影响 signoff 的 unresolved `?` | 保留并列入交付问题清单，**禁止编默认值** |
| `E-TYPE-*` | 宽度/signedness 不匹配 | 补显式 `zext/sext/trunc/as_u/as_s`，不要靠隐式规则 |
| `E-STATE-*` | state 缺/多 next、reset 遗漏 | 回查 spec；缺的是 spec 没说→写 hole / `none` |
| `E-CDC-*` | 跨 domain 未声明同步意图 | 如实保留并提示客户，核心 IR 不内建 synchronizer |
| `E-ABSTRACT-*` | abstract 无 `constrain` coverage | 补 `apply` + contract 的 `constrain` role 绑定 |
| `E-PROV-*` | 映射双向 backlink、stale node、unknown requirement | 用 `specir nodes` 核对真实 ID，修正双向映射 |
| `N-CONTRACT-*` | contract 已定义待 adapter | 信息性；列入 readiness 报告 |
| `W-CHOICE-NOT-PROVEN` | 无 Z3，未证明 | 提示安装 z3 重跑，不要在报告中声称"已证明互斥" |

**关于 `E-CONFLICT-*`（open conflict）**：这是阻断项，正确处置是回到客户澄清，或在 provenance 中标记 `resolved` 并给出 resolution 依据（人工决策记录），而不是删除冲突记录。

### 6. 交付门禁

交付物 = `.specir` + `provenance.json`（+ `contracts.json`，如有 abstract/外部 obligation）+ build bundle。

- 总原则：draft 该怎样就怎样。`specir check` 的 Error/Warning/Note 诊断是编译器对 draft 与文档现状的如实陈述，不构成"交付失败"——只有编译器跑不起来（E-PARSE/崩溃）才说明草稿本身写坏了，必须修。文档缺什么语义就让它缺着，用 hole/conflict + 问题清单提醒用户对齐。
- 理想情况：`specir build --signoff` 退出码 0，bundle 中 manifest 显示 `spec_signoff=true`。
- 有真实 hole/conflict 无法闭环时：**应交付带 hole 的 draft，以提醒用户对齐设计细节**——不得为了"编译通过/零 error"而删掉 hole、删掉整个模块或编造默认值。每个保留的 `?name` / open conflict 必须写入 `spec/questions.json`，并输出同内容的 `NEBULA_DECISION` 决策块（原始证据、具体问题、选项与对 RTL/lowering 的影响）。带 hole 的 draft 退出码为 1 是**正常交付状态**，不是失败。
- hole 的合法位置只有**表达式位置**：state reset 值（`reset ?name`）、常量值（`const X: int = ?name`，仅参与比较/运算）、时序边界（`##[1:?name]`）、分支结果。
  - **禁止**把 hole 写进 `param` 默认值（`E-TYPE-CONST`，编译器正确拦截——param 默认值必须是常量）；
  - **禁止**把 hole 写进位宽（`bits[?w]`）——位宽依赖 hole 会连带 `E-TYPE-WIDTH` 族错误。位宽/参数未决说明接口本身未定：已确定的接口与行为照常写，未决维度不要硬写，交给决策块/问题清单等用户确认后再补全。
- `.specir` 中保留命名 hole 是诚实交付，不得伪造完成。
- 含 `abstract` 的 spec 可以完成 spec-level signoff，但 `design.mlir` 只会在 refinement 后产生；不要为了让 MLIR 生成而删掉 abstract。
- 报告结果时如实陈述：诊断数量、hole 清单、未证明的 choice（W- 级）、contract readiness，以及 round-trip/fmt 是否干净。

## Sidecar schema（v0.1，照此生成）

`provenance.json`：

```json
{
  "schema_version": "0.1",
  "requirements": [
    {
      "id": "REQ-17",
      "classification": "normative",
      "status": "mapped",
      "mapping_kind": "core",
      "evidence": ["irq_spec.docx#blk401"],
      "mapped_nodes": ["<真实 node_id>"],
      "mapped_contracts": []
    }
  ],
  "nodes": [
    {
      "node_id": "<来自 init-provenance 模板>",
      "module": "IRQ",
      "requirements": ["REQ-17"],
      "evidence": ["irq_spec.docx#blk401"],
      "extraction": {"kind": "llm", "model": "...", "prompt_version": "...", "confidence": 0.97}
    }
  ],
  "conflicts": [
    {"id": "C-DONE-BEHAVIOR", "status": "open",
     "candidates": [
       {"claim": "one-cycle pulse", "requirements": ["REQ-12"], "evidence": ["..."]},
       {"claim": "sticky-until-clear", "requirements": ["REQ-91"], "evidence": ["..."]}
     ]}
  ]
}
```

约束：`classification ∈ {normative, objective, assumption, definition, out_of_scope}`；`status ∈ {pending, mapped, question, out_of_scope}`；`mapping_kind ∈ {core, contract, both, none}`。`status=mapped` 时映射必须与 `mapping_kind` 一致且非空；`out_of_scope` 必须 `mapping_kind=none` 且无映射。requirement ↔ node 必须**双向** backlink；node ID 必须真实存在（否则 `E-PROV-STALE-NODE`）。conflict 默认 `open`，open conflict 阻断 signoff。

`contracts.json`：

```json
{
  "schema_version": "0.1",
  "contracts": [
    {
      "id": "CONTRACT_SCORE",
      "requirements": ["REQ-31"],
      "evidence": ["numeric.md#L12-L20"],
      "interface": {
        "input":  {"mode": "observe",   "type": {"kind": "bits", "width": 32}},
        "result": {"mode": "constrain", "type": {"kind": "bits", "width": 28}}
      },
      "semantics": {"language": "math-expression", "body": ["result is an allowed approximation of decode(input)"]},
      "verification": {"backend": "external_numeric_oracle", "adapter": null, "status": "adapter_required"}
    }
  ]
}
```

约束：role mode ∈ `{observe, constrain}`，全部 named binding；`verification.status ∈ {adapter_required, executable, manual}`；`executable` 的 adapter 必须是相对 sidecar 目录可解析的真实可读文件。空 interface 只允许芯片级全局目标，不得用来规避数据依赖，也永远不能覆盖 abstract symbol。

`questions.json`：

```json
[
  {
    "id": "REQ-17",
    "title": "复位方式",
    "context": "需求只写了复位有效电平，未说明同步或异步",
    "options": [
      {"key": "sync", "label": "同步复位", "rationale": "...", "consequences": "..."},
      {"key": "async", "label": "异步复位", "rationale": "...", "consequences": "..."}
    ],
    "recommendation": "sync",
    "blocking": true,
    "status": "open"
  }
]
```

未决项使用稳定 ID；`provenance.requirements[].status=question` 的 ID 必须存在于 open
questions 中。用户决策落实后把对应问题改为 `resolved` 并记录 decision，同时更新
draft 与 provenance；没有未决项也必须写空数组 `[]`。

## 自检清单（交付前逐项确认）

- [ ] 每个需求条目都过了 scope gate；out-of-scope 的有排除理由。
- [ ] `case`/`priority` 的选择与 spec 原文的优先级表述一致，没有按行文顺序脑补。
- [ ] 所有未决定项都是命名 hole `?name` 或显式 `none`；没有编造的默认值/宽度/reset。
- [ ] 无 ontology keyword；无 confidence/metadata 混进 `.specir`。
- [ ] 位宽、signedness、enum 运算全部显式。
- [ ] 每个 state 恰好一个 next equation；组合逻辑无环。
- [ ] abstract 都有 `apply` + `constrain` coverage；明确的外部 obligation 都进了 contract 而非被丢弃或降级成 hole。
- [ ] provenance 用 `init-provenance` 的真实 node ID，requirement ↔ node 双向 backlink 完整；open conflict 已列出。
- [ ] `questions.json` 覆盖所有未决 requirement/hole/conflict；每项都有至少两个可操作选项和同内容决策块。
- [ ] `specir fmt --check` 干净；`specir check` 能完整执行且编码错误已清除，需求缺口导致的诊断原样保留；`build --signoff` 结果如实报告。
- [ ] 交付摘要包含：hole 清单 + 客户问题、未证明 choice、contract readiness、signoff 状态。
