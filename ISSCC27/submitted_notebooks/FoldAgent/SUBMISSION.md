# FoldAgent 提交要求与最终核查

作品：**FoldAgent: Agent-Assisted Logic Folding with Automated Verification**  
作者：Zhanchen Zhao、Wenyu Sun、Yaqing Lai、Yubo Deng  
所有作者单位：Tsinghua University  
赴会代表：Zhanchen Zhao

## 截止时间与提交方式

核对日期：2026-10-31。

**截止：2026-10-31 11:59 AM Pacific Time，即北京时间 2026-11-01 02:59。** 当日美国太平洋时区为 UTC−07:00，北京为 UTC+08:00。

正式提交通过 fork 官方仓库后发起 GitHub Pull Request。目录为：

    ISSCC27/submitted_notebooks/FoldAgent/

使用最终投稿 ZIP 解压出的干净目录，其中仅包含 package-manifest.json 的 files 条目及清单本身，覆盖 FoldAgent.ipynb、LICENSE、README 和必要配套文件。验证工作副本 validation/、运行缓存、浏览器预览及 __pycache__/ 留在作者工作区；上传目录保留 validation.json、revision-validation.json 和 validation-tests.log。PR 的改动应集中在这个项目目录。截止前完成提交和修改；按通用申请指南，截止后保持 PR 内容稳定。

官方来源：
- [ISSCC 2027 当届规则与提交步骤](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/README.md)
- [IEEE SSCS 奖项官网](https://sscs.ieee.org/membership/awards/ieee-sscs-code-a-chip-travel-grant-awards/)
- [通用申请指南](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/howtoapply.md)
- [通用 FAQ](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/FAQ.md)

通用指南仍保留 ISSCC26 的旧路径；本版采用当届首页明确给出的 ISSCC27/submitted_notebooks/ 路径。

## 要求与本包对应

| 官方要求 | FoldAgent 对应材料 |
|---|---|
| 开放许可的 Jupyter Notebook，展示创新电路或教育项目 | [FoldAgent.ipynb](FoldAgent.ipynb)，定位为 agent 辅助逻辑分层与自动化验证的工程教学案例 |
| 使用开源工具，适用时使用开放 PDK | Icarus、Yosys、OpenROAD/OpenRCX、OpenSTA 与 SKY130；固定来源见 [DEPENDENCIES.md](DEPENDENCIES.md) |
| 清楚解释主要思想、设计决策、方法、结果和复现步骤 | Notebook 的设计取舍、流程分工、162 场景比较、局部修复、联合时序及复现入口 |
| Notebook 顶部列出团队成员 | 四位作者及统一单位已列出，代表为 Zhanchen Zhao |
| 包含适当开放许可证 | [LICENSE](LICENSE)、[LICENSE-SCOPE.md](LICENSE-SCOPE.md)、[NOTICE](NOTICE)、[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) |
| 提供引用、注明复用内容和工具版本 | 来源与致谢、sources.json、requirements.txt、DEPENDENCIES.md；平台测量摘录及适用许可单列 |
| 团队指定一位赴会代表 | 已确认 Zhanchen Zhao；获奖后需本人到 ISSCC 2027 并展示项目海报 |
| 最终版图属于鼓励内容 | 已提供两层 GDS、实际版图图像和读回记录 |

当前官方页面列出的核心提交形式是 Notebook 加必要配套文件；本包的 HTML 用于方便阅读。最终版图、完整端到端流程属于鼓励内容。

## 本地最终检查

结果记录见 [revision-validation.json](revision-validation.json)，可运行文稿检查见 [validation.json](validation.json)。

- 同步名称、入口文件、四位作者、单位、赴会代表和已批准许可。
- 在独立副本执行七个现有 Notebook 代码单元和八项检查。
- 核对来源哈希、双语图片/链接、冻结设计及文件清单。
- 沿用 v4 的 324 次 RTL 仿真、三组联合 STA，以及 v5 的 GDS 和图像。
- 本轮新增设计实验为零。

原始来源路径、历史平台名称和阶段编号保留在证据中，供文件身份复核使用。当前项目的对外名称为 FoldAgent。

## 提交操作

1. Fork [官方仓库](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io)。
2. 从最终投稿 ZIP 解压 FoldAgent 干净目录，按 package-manifest.json 核对哈希后放入 fork 的 ISSCC27/submitted_notebooks/。上传范围严格等于清单 files 条目加清单本身。
3. 检查变更范围只含 ISSCC27/submitted_notebooks/FoldAgent/。
4. 发起面向官方仓库 main 分支的 PR，标题可用：**ISSCC27: FoldAgent — Agent-Assisted Logic Folding with Automated Verification**。
5. 截止前完成最终修改，随后关注组织者的问题。

本文件说明投稿材料与操作；线上提交状态以官方仓库的 PR 为准。公开授权及许可证状态见 [PUBLICATION-REVIEW.md](PUBLICATION-REVIEW.md)。
