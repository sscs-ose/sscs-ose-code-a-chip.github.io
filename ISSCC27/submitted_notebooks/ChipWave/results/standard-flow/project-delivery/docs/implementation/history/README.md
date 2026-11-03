# RTL 实现记录

工程判定：**blocked_specification_conflict**。现有 RTL 是待继续处理的实现快照，不能宣称完整满足两份签署规格。发现冲突后没有再改动 RTL、冻结规格、checker 或 vendor IP。

完整读取两份捕获的 Artifact 记录，核对设计原始字节摘要、CSIR signoff 的 source/contracts/provenance 摘要及捕获副本。设计 Artifact 没有单独的 spec_digest 字段；CSIR 的 spec_digest 与 signoff revision_id 一致，其 provenance.file_inputs 中的 design_digest 与设计 Artifact 一致。438 个需求 ID 与设计附录、provenance 一致，792 个节点的需求引用已核对。没有输入 design.dependencies，也没有选用外部 IP。

设计摘要为 sha256:50b5573b1d1c6955de430690ef55a0ff3ccdc3d4aab991669094cab356ec7874；CSIR 修订摘要为 sha256:b0d87b90baa827b87d5542fcbe7d60948825e13a7bd84b180d12fb85f7d73822。CSIR signoff 中 rtl_lowering_ready=false、verification_contracts_ready=false 是原输入状态，本任务没有将其改为 true。

`spec/design_doc.md:123` 要求忽略没有匹配有效 token 的指令数据；第125行明确允许无请求周期的外部数据改变。第129行的实现决策要求 EX 重定向边沿不发请求，在下一边沿请求目标。`spec/draft.specir:388` 却将 id_serial_wait 定义为 `(id_csr || id_mret) && (ex_v || mem_v || wb_v)`，没有 if_v 限定；第504、506行又让它阻塞 imem_valid。IF/ID 被重定向清空后，无主的 CSR/MRET 字样仍可以通过该路径影响执行时序。

最小程序依次为 JAL x1,+8、错误路径 NOP、ADDI x2,x0,2、JAL x0,0。第一条指令第2边沿取指、第4边沿 EX 重定向，文档要求第5边沿取目标。外部无效数据为 deadbeef 时目标实际第5边沿请求；为合法 CSRRS 字样34002073时目标第7边沿请求。后者没有有效 IF/ID token，两个额外气泡来自未限定的 id_serial_wait。两个程序的退休值均正确；冲突是无主数据被忽略的规则及精确重定向实现决策，不能通过文档“源合同不另设控制罚拍上限”来豁免。原始独立自检的无效数据固定为 deadbeef，因此先前通过没有暴露此条件。

复现：`python3 docs/implementation/reproduce_spec_conflict.py`。该脚本构建原始 RTL 与本任务自编 testbench，执行两个合法外部时序场景，写 build/rtl/spec_conflict.json。观察到上述设计规则失败时返回1；这表示工程阻塞被复现，不是工具执行失败。不得用限制合法 imem 无效数据取值、隐藏气泡或擅自改动某一份规格来消除记录。冻结基线责任方须同步并重新签署 fetch ownership / CSR serialization 规则，之后才能继续 RTL 工作。

保留的实现文件按依赖顺序为 rtl/nebula_npu_dot4.sv、rtl/rv32i_five_stage_cpu.sv、rtl/integration/nebula_cpu_npu_top.sv。CPU 默认 ENABLE_XNEBULA=0，顶层显式启用1；两个配置均有真实 IF/ID、ID/EX、EX/MEM、MEM/WB 寄存器组。NPU 只在启用 generate 分支实例化。寄存器写与 commit 在同一 WB 边沿发生，xdot 响应先进入 EX/MEM，再进入 MEM/WB、WB。CPU 包含带源使用标志的转发、load-use 气泡、阻塞 EX 的 WB 操作数刷新、单个 MEM 请求/响应所有权、字节通道、携带 fault 的精确退休及串行 CSR/MRET。当前实现保留了上述 CSIR 原方程，因此不对冲突处的设计合规性作完成声明。

冲突发现前完成的本地检查：Verilator 两配置 lint/elaboration；Yosys 两配置 proc/opt/check；冻结公开64-ADDI冒烟；148 次自编 CPU 运行，逐条比较独立 ISA 解释器的正常/异常退休、实际总线请求和最终完整自检数据区；NPU 穷举65,536组同字节四通道输入、2,000组随机混合通道、10个 kill/reset 取消时点，并检查 n+2、响应背压和消费边沿不接受新请求。CPU 本地用例包括六种 ALU 相关对、五种 load 消费对的三种总线条件、20个固定等待种子、六分支、JAL/JALR、CSR、各异常/MRET、非法 custom、旧 MEM 错误优先、NPU正常流水退休及复位；另对启用配置的64-ADDI逐条检查n+4，对 xdot 检查fetch+7以及下一依赖指令连续退休。这些是本地自检，未声称冻结 CPU-PIPE-CYCLES、ACT4、Sail 或完整验收通过。

可重运行本地检查：`python3 docs/implementation/check_rtl.py`。它保持原deadbeef刺激并将结果写到 build/rtl/selfcheck_results.json；该局部检查的 PASS 不会解除已记录的规格冲突。工具环境需要 C++20；宿主只有 libatomic.so.1，脚本只在 build/rtl/tool-libs 创建链接器名称，没有修改系统库或验证源码。严格 lint 仅对共享 decode/payload 的未使用字段设置 -Wno-UNUSEDSIGNAL；未豁免宽度、锁存器或功能错误。

Yosys 结构结果：默认配置没有 NPU 实例和乘法器；启用配置恰有一个 nebula_npu_dot4 实例、四个乘法器，无除法器。此检查不等于工艺映射、STA 或物理收敛。测试摘要、源码哈希、诚实工程判定和复现结果见 validation.json；每个原始需求的实现绑定或下游责任边界见 requirements.json，它不修改 ledger 审查状态。

未运行冻结 ACT4/Sail 全量、正式定向/随机验收、形式证明、工艺时序或物理流程；integration/design.f、dependencies.lock.json及根目录T09合同文件仍由各自有写权限的下游任务负责。当前最直接风险是未同步的签署规则：现有快照不可作为完整合规 RTL 交付。
