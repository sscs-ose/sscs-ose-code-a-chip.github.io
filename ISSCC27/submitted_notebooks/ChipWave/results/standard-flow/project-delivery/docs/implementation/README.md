# RTL 实现与本地验证

已实现 rv32i_five_stage_cpu、nebula_npu_dot4 和 nebula_cpu_npu_top。本次使用新的签署设计与 CSIR，将 id_serial_wait 限定为有效 IF/ID token 才能触发。无主的 CSR/MRET 字样因此不会阻塞重定向后的目标取指；有有效 token 时仍遵守原 CSR 串行化规则。原规格冲突已由上游同步签署解决。

完整输入记录和捕获副本的字节摘要已核对。设计 Artifact 为 artifact-6892c9f0c47b491c8ac8c08778634f0d，设计 SHA256 为3b2c475adbd277e410da4504911247bb3890d32ccb4fb3651d4003915274784f；CSIR Artifact 为 artifact-971f6c7042664af69515024a25a72bc2，修订摘要为9e2e4dc1c876bda98921b4d26ccea97cad53efc9e5064966c16cbc6a8f2ecec5。CSIR provenance 中的设计摘要与当前设计一致。443个需求、831个节点的引用已检查；需求实现绑定及下游责任见 requirements.json，不改变冻结 ledger 审查状态。

综合文件按顺序为 rtl/nebula_npu_dot4.sv、rtl/rv32i_five_stage_cpu.sv、rtl/integration/nebula_cpu_npu_top.sv。CPU默认ENABLE_XNEBULA=0，集成顶层显式设为1。两配置保留真实 IF/ID、ID/EX、EX/MEM、MEM/WB 级间寄存器，32×32寄存器文件、EX/MEM与MEM/WB转发、同边沿WB读旁路、等待中的操作数刷新及一次load-use气泡。取指响应按请求PC配对，阻塞时捕获；数据端单个请求/响应所有权负责稳定请求、字节通道和背压。异常随指令逐级携带，CSR/陷阱/MRET和RF更新在WB发生，commit/trap公开输出可观察这些行为。

启用generate分支实例化一个NPU，四个有符号8位乘法结果先寄存，再以17位对加、18位总加并符号扩展到32位。独立响应在请求接受后的n+2出现，背压保持结果；kill/reset优先取消工作。xdot由ID/EX拥有，响应进入EX/MEM、MEM/WB后正常退休；没有隐藏累加器或提交延迟队列。默认配置无NPU实例或乘法器，启用配置恰有四个乘法器，均无除法器。外部程序/数据存储器不进入物理顶层。

本次Verilator5.048本地验证和Yosys检查通过：148次CPU运行逐条比对独立自编ISA解释器的正常/异常退休、真实总线请求与最终自检内存；冻结公开64-ADDI冒烟检查n+4和连续吞吐；启用配置也逐条检查64-ADDI n+4，xdot检查fetch+7及下一依赖指令连续退休。用例包含ALU/load相关对、三种固定总线条件、20个等待种子、六分支、JAL/JALR、CSR、异常/MRET、错误路径、旧MEM错误优先、NPU读写回以及复位。NPU检查65,536组同字节四通道输入、2,000组混合随机输入和10个取消时点，覆盖n+2、响应背压及消费边沿不能接受新请求。

原反例回归在两配置分别使用无效数据deadbeef、34002073（CSR）、30200073（MRET）及0，共8次；目标均在规定第5边沿请求，两条退休事件的PC/值正确，且没有错误路径trap或数据请求。这直接验证有效token限定的修复。以前未限定的实现会在CSR刺激下第7边沿才请求目标，旧结果保持为历史证据。

重运行本地完整检查：`source /tmp/chipnebula-pinned-tools/env.sh && source /opt/rh/gcc-toolset-13/enable && python3 -B docs/implementation/check_rtl.py`。

重运行原反例回归：`source /tmp/chipnebula-pinned-tools/env.sh && source /opt/rh/gcc-toolset-13/enable && python3 -B docs/implementation/reproduce_spec_conflict.py`。该文件保留原复现入口名称；现对修复后的签署规则做断言，成功返回0，结果写build/rtl/spec_conflict_resolution.json。

两份环境脚本均在执行各自检查的同一个命令shell中加载，实际版本由子进程探测并记录。严格lint仅豁免共享decode/payload字段的UNUSEDSIGNAL，未豁免宽度、锁存器或功能告警。宿主libatomic缺少开发链接名时，脚本只在build/rtl/tool-libs建立临时链接；C++20参数和该链接仅用于本地仿真构建。没有修改系统库、冻结规格、公共checker或vendor IP。

工程判定及当前源码哈希见validation.json。此前Verilator5.052的本地偏差、通过结果和冲突证据保存在docs/implementation/history以及build/rtl/history-verilator-5.052；没有将它们改称5.048或正式公共结果。本次使用5.048也仍属于本地自检，独立公共覆盖贡献为0、common_coverage_eligible=false。正式公共验收必须由下游验证任务用5.048、两份同shell环境加载证据及独立冻结checker执行，并核对完整运行证据链。

未运行冻结ACT4/Sail全量、正式定向/随机公共验收、形式证明、工艺STA或物理流程。本地数据模型只覆盖4KiB；CPU本身没有硬编码镜像范围，可由外部环境提供签署的256KiB空间。integration/design.f、dependencies.lock.json及根目录T09合同仍由具有相应写权限的下游任务负责。现有本地PASS不替代正式验收或物理收敛。
