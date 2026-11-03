# CPU/NPU detailed architecture freeze

Artifact type: `design.specification`; schema_version: 1. Document kind of the released input: `detailed_design`.

Source artifact: `cpu-npu-requirements`, frozen commit `991e86af716dc8d758554cbbd4ebaf7b5f55fec6`, tree `0942b24de113ce9f636845819a09c06548282e6c`, inline source digest `sha256:ba307c2b5ee170ee22b621bd80e0df4196f7fbceeba329ca4e7eac8ad7ccd33b`. Released classification artifact: `artifact-1ef6aa62e169427a895856a858924777`. Both complete artifact records, the entire inline source, all three frozen specification files, both public testbenches, and both supplied tools were read. The captured and workspace specification copies match byte for byte. The classification supplies no requirements ledger and reports requirement_count=0; the trace identifiers below are local to this design, not invented source-ledger entries.

This document freezes architectural behavior, shared module boundaries and implementation obligations. Circuit organization, RTL expression, multiplier mapping, synthesis choices and placement methods remain with the designers. Only this document is delivered by this architecture task. No RTL, source, checker, manifest, trace collector or software executable is changed here. Appendix A reproduces the full immutable case source; Appendix B preserves the acceptance JSON. The appendices remain normative alongside the expanded design. No source obligation is waived by a shorter description elsewhere.

**Engineering verdict:** the CPU, NPU, software and physical interfaces are specified below. One source-completeness item remains open: the referenced `acceptance.md` is not in the supplied artifact or its frozen Git tree. The three frozen data-bus test conditions and numerical retirement-span budgets cannot be recovered from the supplied public smoke checks. Section 9 gives concrete design timing obligations and a span accounting rule, but does not invent those acceptance values. Until that missing acceptance information is supplied and checked against this architecture, this document does not assert complete performance-contract closure or `unresolved_items=[]`.

## 1. Scope and delivery ownership

The core is a single-issue, in-order RV32I machine with five real stages, a 32-by-32-bit integer register file, M-mode only, the specified eight CSR addresses, Zicsr, and MRET. The only extension configuration is the constant elaboration parameter `ENABLE_XNEBULA`, legal values 0 and 1, default 0. There is no M/A/F/D/C extension, interrupt input or interrupt service, MMU, cache, branch predictor, generic CPU multiplier/divider, operating system, internal program/data memory, DMA, accumulator, saturation or NPU memory interface. The custom dot-product's four small multipliers belong only to the NPU.

CPU delivery owns decode, register file, stage registers, bypasses, memory protocol, CSR/trap state, NPU issue/cancellation ownership and retirement. NPU delivery owns signed DOT4 arithmetic and its fixed handshake timing. Integration delivery owns an exact-port wrapper, configuration and reproducible source manifests; it cannot change CPU or NPU protocol. The released classification is consumed as input, not rerun to reinterpret the contract.

`rv32i_five_stage_cpu #(ENABLE_XNEBULA=0)` is the base public module. For parameter 0 an explicit generate alternative has no NPU instance, no NPU wait, and traps every instruction whose opcode is custom-0 (`7'h0b`). For parameter 1 an explicit generate alternative instantiates exactly one `nebula_npu_dot4` and recognizes only the encoding in section 7. The base ISA, CSR values (including misa), memory interfaces and base timing obligations remain unchanged in both configurations.

`nebula_cpu_npu_top` has no additional external port or run-time extension control. It instantiates the core with `ENABLE_XNEBULA=1` and connects every external port without functional reinterpretation. No NPU ports escape this top. Designers supply `integration/design.f` and `dependencies.lock.json`; this task specifies them but does not write them. The file list must explicitly order NPU dependencies/module, CPU dependencies/module, then the integration wrapper, with packages preceding their users. The lock identifies exact files, revisions/content digests, top `nebula_cpu_npu_top`, parameter value 1, and the base-core parameter-0 verification configuration. No glob order, stale source, black-box NPU or hidden reference implementation may determine the build.

## 2. Complete shared ports

Directions below are relative to the named module. All values are binary logic signals with the listed bit widths. No extra architectural ports are permitted. All handshakes sample on rising `clk` edges; `rst_n` is active low. Reset must work while asserted, clear all valid/ownership state, and prevent visible transactions; release is assumed stable for the receiving clock edge. Whether internal reset distribution is synchronous or asynchronous is a designer choice consistent with these observable requirements.

### 2.1 CPU and integration top: identical 27 ports

This table is the complete port list of both `rv32i_five_stage_cpu` and `nebula_cpu_npu_top`, matching `tb/public_cpu_tb.sv` (7 inputs, 20 outputs).

| Port | Direction | Width | Contract |
|---|---|---:|---|
| clk | input | 1 | Single CPU/NPU clock |
| rst_n | input | 1 | Active-low common reset |
| imem_valid | output | 1 | Fetch request sampled each rising edge when high; no ready input |
| imem_addr | output | 32 | Byte PC, four-byte aligned for every issued request |
| imem_rdata | input | 32 | Ordered one-cycle synchronous instruction response |
| dmem_req_valid | output | 1 | Held request offer until ready handshake |
| dmem_req_ready | input | 1 | External request acceptance |
| dmem_req_write | output | 1 | 0 load, 1 store |
| dmem_req_addr | output | 32 | Aligned word address, effective address with bits [1:0] zero |
| dmem_req_wdata | output | 32 | Store source placed in addressed lanes; 0 for loads |
| dmem_req_wstrb | output | 4 | Per-byte store mask; 0 for loads |
| dmem_rsp_valid | input | 1 | Held completion for one accepted request |
| dmem_rsp_ready | output | 1 | Accept completion only with matching outstanding owner and storage capacity |
| dmem_rsp_rdata | input | 32 | Full little-endian word for loads |
| dmem_rsp_err | input | 1 | Access error; erroneous store has no memory side effect |
| commit_valid | output | 1 | One normal WB retirement event per cycle; consecutive events may keep it high |
| commit_pc | output | 32 | PC of that retired instruction |
| commit_insn | output | 32 | Exact retired instruction word |
| commit_rd | output | 5 | Written nonzero destination, otherwise 0 |
| commit_wdata | output | 32 | Actual architectural destination value, 0 when commit_rd=0 |
| commit_mem_addr | output | 32 | Successful retired store's aligned bus address, otherwise 0 |
| commit_mem_wstrb | output | 4 | Successful retired store mask, otherwise 0 |
| commit_mem_wdata | output | 32 | Successful retired store's lane-positioned bus data, otherwise 0 |
| trap_valid | output | 1 | Precise trap event, distinct from normal retirement |
| trap_pc | output | 32 | Faulting instruction PC |
| trap_cause | output | 32 | Synchronous exception cause with interrupt bit zero |
| trap_tval | output | 32 | Fault address/instruction or zero as defined in section 6 |

No imem_ready, imem response-valid, instruction error input, bus ID, byte-addressed data request, interrupt, debug or NPU debug port is added. Commit/trap values are meaningful with their respective valid signals; valid signals default to zero on cycles without events, and all observation outputs clear on reset. Observation ports never feed execution logic. Store commit fields use the actual accepted bus transaction; the full effective byte address is carried separately inside the pipeline for alignment and mtval. Load retirement has commit_mem_wstrb=0 even though it accessed memory. rd=x0 always yields commit_rd=0 and no register write.

### 2.2 NPU: complete 10 ports

| Port | Direction | Width | Contract |
|---|---|---:|---|
| clk | input | 1 | Same clock as CPU |
| rst_n | input | 1 | Common active-low reset |
| req_valid | input | 1 | Request offer held until handshake |
| req_ready | output | 1 | Can accept one request when idle and not reset/killed |
| req_a | input | 32 | Packed rs1 operand, byte 0 in bits [7:0] |
| req_b | input | 32 | Packed rs2 operand, byte 0 in bits [7:0] |
| rsp_valid | output | 1 | Fixed-latency result, held until handshake |
| rsp_ready | input | 1 | CPU ready to capture result into normal execution pipeline |
| rsp_data | output | 32 | Signed INT32 dot-product in two's-complement bits |
| kill | input | 1 | Cancellation dominates request/response and clears all work |

The CPU wires these ports only inside the enabled generate block. There are no tags because the CPU and NPU maintain a single shared owner, no interrupt response, and no sideband destination/address/accumulation field.

## 3. Instruction architecture and reset

PC resets to `0x8000_0000`. x0 reads as zero on every operand path, is excluded from dependency comparisons, and cannot be written. The other GPRs have no source-guaranteed reset values; software must initialize them before use. Register file storage remains exactly 32x32 bits; pipeline operand/result registers and bounded fetch buffering are not additional architectural register files. CSR reset values are in section 6. Reset empties all four stage boundaries, fetch-response tracking, buffers, data-bus ownership, NPU ownership, issued flags and retirement/trap pulses. CPU, NPU and external memory reset together; external memory discards in-flight data requests and instruction responses. Nothing from before reset can retire or complete after release.

Instructions are 32 bits, IALIGN=32; there is no compressed decode. All arithmetic wraps modulo 2^32 except comparisons and sign extensions interpreted as described below. Valid base HINT instructions, including instructions whose destination is x0, still retire once without an architectural register write. Legality is decoded from the complete instruction encoding, not just opcode. Unsupported extensions and reserved encodings outside the supported ISA trap with cause 2.

| Family | Opcode / legal discriminator | Complete behavior |
|---|---|---|
| LUI | 0x37 | rd = insn[31:12]<<12 |
| AUIPC | 0x17 | rd = instruction PC + U immediate |
| JAL | 0x6f | rd = PC+4; target PC + sign-extended J immediate |
| JALR | 0x67, funct3=000 | rd = PC+4; target = (rs1 + sign-extended I immediate) & ~1; then check bits [1:0] |
| Branch | 0x63; funct3=000,001,100,101,110,111 | BEQ, BNE, BLT, BGE, BLTU, BGEU; signed for LT/GE, unsigned for LTU/GEU; taken target PC + sign-extended B immediate |
| Load | 0x03; funct3=000,001,010,100,101 | LB, LH, LW, LBU, LHU; address rs1 + sign-extended I immediate |
| Store | 0x23; funct3=000,001,010 | SB, SH, SW; address rs1 + sign-extended S immediate; store low source byte/halfword/word |
| OP-IMM | 0x13; funct3=000,010,011,100,110,111 | ADDI, SLTI, SLTIU, XORI, ORI, ANDI; 12-bit immediate sign extended including the unsigned SLTIU comparison operand |
| Immediate shifts | 0x13; funct3=001 or 101 | SLLI uses upper immediate bits 0000000; SRLI uses 0000000; SRAI uses 0100000; shamt=insn[24:20]; other upper bits illegal |
| OP | 0x33 | funct7=0000000 supports ADD/SLL/SLT/SLTU/XOR/SRL/OR/AND for funct3=000..111; funct7=0100000 only SUB (000) and SRA (101); other combinations illegal |
| Register shifts | OP subset above | Shift count rs2[4:0]; SRA sign-fills, SRL zero-fills |
| FENCE | 0x0f, funct3=000 | Ordered no-op on the single-transaction memory system; no memory request. pred/succ are honored by existing ordering; reserved fm/rs1/rd fields do not add operations and are treated conservatively as a base FENCE |
| FENCE.I | 0x0f, funct3=001 | Unsupported: illegal-instruction trap |
| ECALL | exactly 0x00000073 | M-mode environment call, cause 11, no normal retirement |
| EBREAK | exactly 0x00100073 | Breakpoint, cause 3, no normal retirement |
| MRET | exactly 0x30200073 | Return in M-mode as section 6; normal retirement once |
| Zicsr | 0x73; funct3=001,010,011,101,110,111 | CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI; section 6 |
| Xnebula | 0x0b; funct7=0000000, funct3=000 | Only enabled xdot4 as section 7; otherwise illegal |

S/B/J immediates are assembled using their ISA bit positions, including the implied low zero for branch/jump offsets; I and U fields retain their defined widths. Loads/stores are little endian. Not-taken branches do not fault on a hypothetical unaligned branch target. For taken branches/JAL/JALR, target alignment is checked before redirect or link write. JALR clearing bit 0 does not permit target bit 1 to be set. No fetch to an unaligned target is emitted.

## 4. Five real stages, four boundaries, and exact timing

### 4.1 Stage functions and transferred state

Every stage token has a valid bit, PC, original instruction (once available), destination/write-enable, and exception state. Invalid entries are bubbles and never cause effects. The four boundary groups have independent valid/advance/hold/clear control; a single multi-cycle instruction FSM with delayed commit pulses does not satisfy this design.

| Stage | Work | State carried into its next boundary |
|---|---|---|
| IF | Select sequential PC or winning redirect; check fetch alignment; offer one imem request; associate fixed-latency return with the sampled PC and stream identity | IF/ID: request-valid/return-valid association, PC, PC+4, stream identity, and live-response versus held-instruction ownership; saved instruction word when the response must be buffered |
| ID | Use the matching instruction response; complete encoding validation, immediate assembly, operand usage decode, two GPR reads and WB-to-read bypass; discover load-use hazard | ID/EX: valid, PC, insn, PC+4, rs1/rs2 numbers, source-used flags, read values, immediate, rd, reg-write flag, ALU/comparison selection, branch/jump/MRET flags, memory size/sign/write flags, CSR address/op/source/write intent, xdot flag and exception cause/tval |
| EX | Select newest forwarded operands; ALU/shift/compare and effective address; validate target and memory alignment; form masks/data; CSR value/result preparation; execute or wait for the owned NPU operation | EX/MEM: valid, PC, insn, rd/write flag, ALU/link/CSR/NPU result, full effective address, aligned bus address, lane/size/sign, store data/strobes, CSR write candidate, exception record, and memory offered/accepted ownership |
| MEM | Own the single data transaction, hold through ready/response waits, recognize errors, extract/extend loads; pass non-memory results once | MEM/WB: valid, PC, insn, rd/write flag, final register result, successful-store bus fields, CSR update or MRET action, and final exception record; a store is eligible only after a successful response |
| WB | Retire the oldest token once: update GPR/CSR or enter trap; emit matching commit or trap observation at the same edge; perform architectural return/trap redirect | No later commit-delay stage; retirement removes the MEM/WB token |

The IF/ID boundary must account for the synchronous external instruction register. At request edge n, internal IF/ID PC/valid/identity metadata is registered, and the external memory registers the corresponding imem_rdata after that same edge for the following ID cycle. ID uses that returned instruction together with the registered metadata during n..n+1. On the unstalled path, the CPU must not add an internal instruction-copy edge before decode: doing so would shift retirement to n+5. The IF/ID group is a real registered data/control boundary even though its normal-path instruction data is held by the contracted synchronous memory output. Its held-instruction register is used when ID cannot consume the live return. This is not combinational/asynchronous instruction memory, decoding an unrequested word, collapsing ID into IF, or adding a fictitious stage.

IF/ID buffering must preserve a blocked head and any already-issued following response. A bounded two-entry head/return arrangement suffices for a one-cycle memory: snapshot the old live return before the external output changes, retain the following request's PC and returned instruction, and stop new fetches once no capacity remains. An equivalent implementation is permitted if it reserves storage for every irrevocable request. Buffer entries do not create an extra stage on the no-stall path. Fetch metadata and instruction words cannot be overwritten while a blocked instruction owns them. Because imem has no ready signal, suppressing future imem_valid is the only backpressure; all accepted returns must be consumed or deliberately discarded as wrong path, never silently lost.

### 4.2 Required no-stall edge sequence

For instruction I, with no dependency, redirect or waiting resource:

| Edge | State/action for I immediately after that edge |
|---|---|
| n | IF request sampled; IF/ID records I's PC/valid; matching instruction becomes available for ID in the next cycle |
| n+1 | ID/EX captures decoded I and its operand/control data |
| n+2 | EX/MEM captures actual execution result and flags |
| n+3 | MEM/WB captures actual final result |
| n+4 | WB writes I's GPR if applicable and emits I's commit observation |

I+1 follows one edge behind I in every stage. The 64 independent ADDIs must therefore have request edges n0..n0+63 and retirement edges n0+4..n0+67, each adjacent pair separated by one cycle. Their first-to-last retirement span is 63 cycles. Neither pipeline filling nor register-file read/write policy may add bubbles. This remains required with ENABLE_XNEBULA=1 when executing the same base sequence.

The WB event is the actual GPR write edge. There is no early GPR write with a later trace, no repeated write on a held stage, and no counter delaying commit to disguise a shorter pipeline. Stores can affect external memory only through a precisely owned accepted transaction, then retire only after its successful response. Their external effect may precede the observation while that transaction is in flight; this is an ordered acknowledged store, not an early instruction retirement.

### 4.3 Advancement, waits and control priority

A stage advances only when its token is ready and the next boundary can accept it. Otherwise it holds all payload and its ownership flags. WB may drain an older ready instruction while younger stages wait; after draining it must clear validity and cannot repeat the event. A blocked MEM freezes EX and younger stages as needed, and suppresses unsafe side effects. A waiting xdot4 freezes its EX owner and younger stages, while older MEM/WB instructions finish. Bubbles can drain forward. A load-use interlock holds IF/ID, prevents the consumer entering EX prematurely, and inserts only the permitted one dependency bubble beyond any shared bus wait.

Priority is reset, then oldest architectural trap/return redirect and cancellation, then safe older control-flow redirect, then resource hold/interlock, then ordinary advance. Age wins over stage-local event detection: an older data error wins over a younger branch, CSR, illegal instruction or xdot4. A redirect/flush invalidates every younger stage and every younger buffered/live instruction return, including one that arrives after the redirect. All tokens retain age/order implicitly through their stage/queue positions. Redirects do not cause the triggering legal branch/jump itself to retire twice or disappear.

A fetch stream identity or equivalent outstanding-request invalidation associates each fixed-latency response with its request. A redirect kills previous-stream younger requests; there are no bus response tags to rely upon. Issue restarts at the winning target. No branch prediction is present; normal fetch uses PC+4. Branches/JAL/JALR resolve operands and targets in EX. A correct taken redirect may flush IF/ID plus the current return; it never bypasses an older unresolved fault. If an older instruction is blocking, retain the redirect decision until it is safe. MRET and trap redirects are architectural WB actions as section 6.

### 4.4 Forwarding and dependency cases

Forward both used operands independently, including branch comparison, JALR base, load/store address, store source, CSR register source and both xdot operands. The newest older matching producer wins: ready EX/MEM result, then ready MEM/WB result, then register-file value with same-edge WB bypass. A not-yet-ready matching producer causes a hold; it must not fall through to an older stale value. A killed, invalid, excepting or rd=0 producer never forwards. Load EX/MEM address is never forwarded as load data. Source-unused instruction fields never create dependencies.

Adjacent and one-gap ALU chains, two simultaneously dependent operands, WAW reuse of one destination, and x0 source/destination cases require no additional ALU bubble. ALU/link results are available after EX; MEM/WB and WB-to-ID bypass cover older producers without relying on a simulator-specific register-file read-during-write behavior. Store data is forwarded as well as the address base; if necessary a final source bypass at the memory boundary ensures that the selected store value belongs to the newest producer. No replayed store request may substitute a later register-file value.

A load immediately followed by a true user is detected from the load destination and the consumer's actual used sources. The consumer waits for successful extracted load data and receives it via the final-result bypass; the hazard contribution relative to an independent sequence with identical external timing is at most one cycle. Additional cycles waiting for request ready or response valid are bus waits, common to the compared sequences. A store whose address or data depends on a load obeys the same bound, as do branch/JALR/CSR/xdot operands. A load to x0 still performs alignment/error checks and its memory transaction, but creates no register dependency. Two consecutive memory instructions never create two simultaneous outstanding transactions. Read/write of CSR state is separately ordered; serialization needed for CSR/trap/MRET does not relax ordinary ALU or load-use requirements.

## 5. External instruction/data memory

### 5.1 Instruction requests

A request is accepted at every rising edge with imem_valid=1. imem_addr is a byte address held stable through that edge. The corresponding imem_rdata is driven in the following cycle by the one-cycle synchronous memory, strictly in request order, one request per cycle possible. There is no response handshake or fetch access error. Only the return of a tracked previous valid request may enter ID. A value present after a cycle with no accepted request is not an instruction. Issued wrong-path requests may return and are discarded; they do not decode, trap, issue memory/NPU work, write or retire. Alignment is checked before imem_valid; any architectural attempt to execute an unaligned PC is a cause-0 event without an unaligned bus request.

### 5.2 Data request and response ownership

A request accepts at edge q iff dmem_req_valid && dmem_req_ready. Once offered, write/address/data/strobes remain stable until that handshake, unless common reset cancels it. Do not pulse valid and lose the request under ready=0. After acceptance, an issued flag removes the offer even if MEM holds for many cycles. Exactly one request is outstanding until a response handshakes at edge s with dmem_rsp_valid && dmem_rsp_ready. An accepted request receives one response within the frozen 1–8-cycle external latency; a held response remains valid and its data/error remain stable until consumed. Both stores and loads require a response. There is no combinational zero-cycle completion requirement. Valid/error alone without ownership cannot retire any instruction.

For the fastest legal bus, make a memory request eligible at the EX-to-MEM boundary once effective address, alignment, store value and all older fault checks are resolved. This boundary offer must use the same values held by EX/MEM if ready is low; it must not expose an unstable candidate when older blocking work could change priority. Thus a request can accept on entry to MEM without a redundant request-setup bubble. MEM captures its handshake response into MEM/WB; WB retires on the next edge. If an external model first raises rsp_valid just after an edge, its handshake is on the next rising edge, not at the just-passed edge. Implementations and span checks must count handshake edges consistently. Once a previous response completes successfully, the next eligible request may accept at the same boundary edge without ever creating two outstanding owners; an older error suppresses the new acceptance. An implementation that cannot safely reuse that edge must still meet the frozen span budgets; this document does not grant an extra setup penalty.

The oldest unresolved memory instruction blocks any younger irrevocable action. A younger store cannot be offered speculatively behind an older possible trap; a younger CSR cannot update state; a younger NPU cannot become a commit candidate. Since the bus has no kill, an accepted transaction must be completed or canceled by common reset. Trap/branch handling must not orphan it. For data-error traps, the response itself completes ownership before trap entry. For successful stores, the memory may apply the write at acceptance or later, but must guarantee no effects on an error response. The CPU only counts a store as successful after response acceptance and cannot issue it on a path that an older event can kill. No instruction-side cancellation fabric is assumed for data memory.

### 5.3 Alignment, lanes and response extraction

Let E=(rs1+immediate) modulo 2^32, lane=E[1:0], and A=E & 0xfffffffc. Bytes permit any lane; halfwords require E[0]=0; words require E[1:0]=0. An alignment failure records E, causes no request, and takes priority over any hypothetical access error.

| Access | Bus address | Store wstrb / wdata | Load result from full word R |
|---|---|---|---|
| byte | A | 0001 << lane; (rs2 & 0xff) << (8*lane) | R shifted by 8*lane; LB sign-extends bit 7, LBU zero-extends |
| halfword | A | 0011 << lane; (rs2 & 0xffff) << (8*lane), lane 0 or 2 | Shift by 8*lane; LH sign-extends bit 15, LHU zero-extends |
| word | E=A | 1111; rs2 | LW returns all 32 bits |

Inactive store lanes are zero-filled in wdata; loads have req_write=0, wstrb=0, wdata=0. dmem_rsp_err converts a load/store to cause 5/7 with mtval=E, not A. Faulting loads cannot write a destination, including any stale result captured before error recognition. Faulting stores have no commit event or memory side effect. A successful store's commit fields equal the accepted A/mask/positioned data; a successful load's commit_wdata equals its selected extended value. Effective address and lane remain fixed through backpressure.

### 5.4 External image and MMIO boundary

Instruction and data ports address the same externally provided 256-KiB image beginning at `0x8000_0000`, ending at `0x8003_ffff`. The external memory/test environment owns image contents, permissions/access-error injection and bus timing; the CPU does not implement that image internally or infer a SRAM from it. `0x8003_F000` is external tohost MMIO: writing 1 means pass and other nonzero values mean failure to the environment. The core handles it as an ordinary store with lane strobes and a response; it cannot special-case the address or synthesize a pass. Values outside the image are handled by the external memory contract; no invented CPU address-map trap replaces a bus error. Cache/self-modifying-code coherence features are outside scope and FENCE.I is illegal.

## 6. Precise exceptions, CSR and retirement

### 6.1 Fault records and retirement ordering

Detect illegal encodings/CSR addresses in ID, target/alignment faults in EX, and access errors in MEM, but defer architectural trap state to the faulting token's ordered WB decision. The exception record disables register/CSR/store/NPU effects and carries cause, faulting PC and tval. Early detection can stop and invalidate younger work, but cannot update mepc or emit trap ahead of older retirement. All older instructions finish; no younger instruction commits. At most one architectural event is emitted in a cycle: either a normal commit or a trap, never both for the same instruction. The faulting instruction does not count as a normal retirement.

| Cause | Event | mepc/trap_pc | mtval/trap_tval |
|---:|---|---|---|
| 0 | Instruction address misaligned | PC of responsible taken branch/JAL/JALR; if fetch PC itself is faulty, that PC | Target after JALR bit-0 clearing, or offending fetch PC |
| 2 | Illegal instruction, unsupported custom encoding/disabled custom-0, unsupported or illegally written CSR, FENCE.I | Faulting instruction PC | Original full 32-bit encoding |
| 3 | EBREAK | EBREAK PC | 0 |
| 4 | Load address misaligned | Load PC | Full effective byte address E |
| 5 | Load access error | Load PC | E |
| 6 | Store address misaligned | Store PC | E |
| 7 | Store access error | Store PC | E |
| 11 | M-mode ECALL | ECALL PC | 0 |

The instruction causing a misaligned control target does not write its link register. A target on a not-taken branch is not checked as a realized fault. Alignment precedes any memory request; access-error priority cannot override a misaligned access because no such request exists. Invalid encodings do not execute their apparent load/store/jump behavior. There are no imem-error, interrupt, page-fault, user-mode or supervisor-mode causes.

On trap entry, atomically write mepc=fault PC with bits [1:0] masked, mcause=cause, mtval=tval, MPIE=old MIE, MIE=0, MPP=3. Redirect to committed direct-mode mtvec and flush all younger instructions/returns. The trap observes CSR state after every older committed CSR update. NPU cancellation follows section 7; a killed token cannot later escape through a stale response. Reset takes precedence over trap entry.

### 6.2 Complete CSR state

| Address | Name | Read/reset | Write semantics |
|---|---|---|---|
| 0x300 | mstatus | Visible MIE bit3, MPIE bit7, MPP bits12:11=11; reset 0x00001800 | Only MIE/MPIE stored; MPP forced 3; other bits read 0/write ignored |
| 0x301 | misa | Read-only 0x40000100 in both parameter configurations | A requested write is illegal; custom extension does not alter this frozen value |
| 0x305 | mtvec | Reset 0x80000000; direct mode only | Store value & 0xfffffffc; mode bits read 00 |
| 0x340 | mscratch | Reset 0 | Full 32-bit read/write |
| 0x341 | mepc | Reset 0 | Store value & 0xfffffffc; also masked on trap entry |
| 0x342 | mcause | Reset 0 | Full 32-bit software read/write; hardware trap writes the listed cause |
| 0x343 | mtval | Reset 0 | Full 32-bit read/write |
| 0xf14 | mhartid | Read-only 0 | A requested write is illegal |

All other CSR addresses, including counters/debug/supervisor CSRs, are illegal. Having no interrupts does not remove the visible MIE/MPIE semantics. Software writes to mcause/mtval are not artificially restricted to hardware-generated values.

For each CSR instruction read the old committed value C, compute source S from forwarded rs1 or zero-extended five-bit zimm, and return C to rd if rd!=0. CSRRW/CSRRWI always request a write of S, including zero source; rd=x0 suppresses reading for architectural side effects but does not waive address/write legality. CSRRS/CSRRSI request C|S; CSRRC/CSRRCI request C&~S. For the register forms, rs1's encoded register number x0 suppresses the write; a nonzero register containing zero still requests a write and is illegal on read-only CSRs. For immediate forms, zimm=0 suppresses the write. Suppressed-write set/clear operations can legally read misa/mhartid. Apply each CSR's mask/forced bits to the candidate before architectural storage.

CSR operations are ordered at WB. Compute C only when older CSR/trap actions are known, using a correct CSR bypass or serialization; a younger CSR never reads stale state. A pending CSR update may be carried in stage data, but becomes visible only with that instruction's normal WB commit. Illegal CSR operations do not write rd or CSR. Trap entry and MRET see the most recently committed CSR values.

MRET is legal only in this M-mode implementation and uses exact encoding 0x30200073. Wait until older work is settled, then at its WB event set MIE=old MPIE, MPIE=1, MPP=3 and redirect PC to mepc. mepc is already four-byte aligned because its writes are masked. MRET emits exactly one normal commit with rd=0 and mem_wstrb=0, and flushes younger work. It is not a trap. Speculative fetch while MRET is pending may be held or discarded but cannot retire past the return.

### 6.3 Commit gating and invariants

WB normal commit requires a valid ready MEM/WB token without exception and without cancellation. Its register write, CSR update and observation arise from one event. WB trap requires the oldest excepting token and emits only trap observation. Every valid nonfaulting instruction, including stores, FENCE, branches, jumps, CSR reads, MRET and xdot4 rd=x0, has exactly one normal event. Every faulting instruction has exactly one trap event; wrong-path/killed/bubble tokens have none. A held stage cannot retrigger any event. Non-store commit_mem_wstrb=0; no-register-write commit_rd=0. Observers cannot affect progress. No trace file or trace recorder is required.

## 7. Xnebula and NPU transaction

### 7.1 Instruction bits, operands and arithmetic

`xdot4 rd,rs1,rs2` is R type: insn[31:25]=0000000, [24:20]=rs2, [19:15]=rs1, [14:12]=000, [11:7]=rd, [6:0]=0001011 (0x0b). Every rs1/rs2/rd index 0..31 is legal in that encoding when enabled. Any other funct3/funct7 under custom-0 traps even when enabled; all custom-0 words trap when disabled. Other unsupported custom opcodes remain illegal.

Take the newest correctly forwarded 32-bit rs1 and rs2 values, snapshot them for the owned request, and interpret lane i as signed bits [8*i+7:8*i] for i=0..3. Compute four independent signed 8x8 products in parallel. Each product requires signed 16 bits; sign-extend before addition. Two-product intermediates require 17 signed bits and the four-product reduction requires at least 18 signed bits (or use 32-bit signed intermediates). The final mathematical range is -65024..65536, so sign extension to INT32 is exact. Return the two's-complement 32-bit sum. Do not truncate partial additions to 16 bits, treat unsigned slices as signed without extension, saturate, retain an accumulator or touch memory.

Reference arithmetic examples (derived requirements, not measurements): 0x80808080 dot itself = 65536 (0x00010000); against 0x7f7f7f7f = -65024 (0xffff0200); 0x7f7f7f7f dot itself = 64516 (0x0000fc04); 0x04030201 dot 0x01020304 = 20. Lane zero is the low byte. Source registers, memory and CSR state are not changed by the operation; rd=x0 only discards destination write after normal execution.

### 7.2 NPU edge protocol

Use these observable phases or an equivalent circuit: IDLE, accepted operands/products, reduction, HELD_RESPONSE. A single busy/valid owner covers execution and held response. req_ready is high only in IDLE when rst_n=1 and kill=0; no request is accepted while executing or holding a response. It is permissible to become ready in the cycle after response consumption; no required same-edge consume/reaccept throughput is invented.

| Edge/interval | Required behavior for request accepted at n |
|---|---|
| Before n | req_valid && req_ready with stable req_a/req_b offers one operation |
| n | Capture operation; req_ready drops while busy; rsp_valid remains 0 |
| n+1 | Advance real product/reduction work; rsp_valid still 0 |
| Immediately after n+2 | rsp_valid=1 and exact rsp_data become stable, independent of rsp_ready |
| Every subsequent edge with rsp_ready=0 | Keep rsp_valid=1 and identical data |
| First subsequent edge with rsp_valid && rsp_ready | Consume once; clear response/busy after that edge |

Because rsp_valid is first asserted after n+2, it cannot also be consumed by a synchronous receiver at n+2 using the newly assigned value. Earliest consumption is n+3 when ready is already high. Do not suppress the n+2 valid observation merely because ready is high. Latency is the response-production latency, not a delayed ready-dependent computation. Inputs req_a/b may change after request acceptance without affecting the result.

When req_valid=1 and req_ready=0, the CPU holds operands/valid until handshake or cancellation. On reset, clear pending products, counters/phase valid, response valid and ownership; req_ready/rsp_valid are not asserted during reset. On any edge with kill=1, discard all pending and held work, produce no accepted request and no consumed/delivered response at that edge, and clear rsp_valid. Gate externally visible ready/valid with reset/kill so high stale values do not appear as successful handshakes. Precedence is reset, kill, existing work/response, request acceptance. This includes kill at acceptance, at n+1, at result production, or while a response is backpressured. After kill is released, a fresh operation can be accepted from idle; no delayed output from the canceled operation may reappear. Kill has no memory/GPR side effects.

### 7.3 CPU ownership, wait and normal writeback

Only a valid, enabled, legal, nonfaulting, correct-path xdot4 in EX can offer a request. Its operands obey section 4 forwarding/load-use rules; the CPU waits for any older unresolved data fault before issue. Freeze PC/insn/rd/write flag and the two actual operands with the EX owner. A not-yet-accepted offer and an accepted transaction are different states; an issued bit prevents duplicate acceptance while EX holds. req_valid is cleared after its one handshake.

During acceptance/execution/response wait, hold the xdot4 EX token and younger ID/IF/buffer tokens, and stop fetch when credit runs out. Older MEM/WB work drains normally. No younger instruction issues an irrevocable request or retires ahead of the dot product. rsp_ready is asserted only when the matching EX owner exists, no cancellation is taking precedence, and EX/MEM can capture the result. A valid held response remains in the NPU until that capture is possible.

On the response handshake, capture rsp_data as the EX result in EX/MEM together with the original instruction metadata. The NPU owner is released exactly once. Then normal MEM pass-through captures the result into MEM/WB, and normal WB writes rd if nonzero and emits one commit. There is no direct NPU-to-register-file write, no direct NPU-to-commit observation, no synthetic commit timer and no duplicate retirement on valid staying high. For an otherwise idle core, a request accepted at a can produce its response after a+2, capture EX/MEM at a+3, MEM/WB at a+4 and commit at a+5. This is an architectural sequence illustration, not a new extension latency limit; downstream older work can delay capture/retirement while the NPU's a+2 production contract remains exact.

Once EX/MEM owns the result, normal forwarding makes it available to a dependent younger ALU/store/branch/CSR/xdot instruction. Resume younger stages when EX is released and dependency readiness permits. rd=x0 still waits for the valid operation and retires once with commit_rd=0; it does not create a dependency. Back-to-back xdot4 instructions each have separate request, result and retirement ownership.

If reset, older trap, older redirect, or flush invalidates the EX owner, assert kill, clear any not-yet-accepted offer/issued owner, and inhibit response capture even if rsp_valid/rsp_ready were previously high. Clear any younger result tokens already in EX/MEM or MEM/WB as part of the same age-based flush. A stale response without a live owner is never used as another instruction's result. Conservative issue ordering prevents an older late fault after launch where possible, but cancellation remains mandatory. A branch cannot redirect on a younger wrong-path xdot4's behalf. ENABLE_XNEBULA=0 never offers requests and never waits for nonexistent NPU responses.

## 8. Software and physical boundaries

### 8.1 Required exact-output workloads

Input bytes represent signed INT8 -128..127; packed words store the first term in the low byte. Outputs and accumulated sums are signed INT32. Accumulation uses ordinary CPU ADD/ADDI after xdot4 partial sums. There is no M-extension instruction, implicit NPU accumulation, saturation or software-visible hidden state. Packing uses legal byte/word loads and RV32I shifts/masks/OR, or aligned software-packed external arrays. Do not issue unaligned LW for arbitrary byte positions. Partial groups are explicitly zero-padded in registers/buffers; software must not overread outside an input array.

| Program | Mathematical contract | Required dot grouping |
|---|---|---|
| DOT64 | One sum of A[k]*B[k], k=0..63, two signed 64-byte vectors | 16 four-term xdot4 results accumulated by CPU ADD |
| signed INT8 GEMM8 | C[i,j]=sum(k=0..7) A[i,k]*B[k,j], i,j=0..7; two 8x8 matrices, 64 INT32 outputs | Two four-term dot products per output (128 total); gather/pack B columns or software transpose them in external storage |
| CONV3 | Y[i,j]=sum(u=0..2,v=0..2) X[i+u,j+v]*K[u,v], X=8x8, K=3x3, valid window i,j=0..5 | 6x6/36 INT32 outputs, no input padding; flatten each nine-term window into two full dot groups and one group with term 9 plus three zero lanes (108 total) |

These counts describe software decomposition, not measured speed. Row-major external arrays and little-endian INT32 output words provide the integration data layout; any checker-specific addresses/input values are supplied by the immutable program fixture, not hardcoded into the CPU. The convolution formula is the usual forward sliding-window stencil without reversing kernel indices; a fixture that defines mathematical kernel reversal must supply the appropriately indexed K to this same dot computation. Initialize every accumulator and temporary GPR. The maximum magnitudes of these short sums fit INT32 without saturation.

Each workload must compare all outputs to an independent signed software reference and report failure on any mismatch; writing tohost is a normal acknowledged store only after checking results. An independent reference cannot reuse NPU output as its golden answer. Host reference arithmetic may use wider signed temporaries. ENABLE_XNEBULA=0 validation uses the base ISA and verifies custom trapping; a scalar workload counterpart, if required by evaluation, uses RV32I shift/add signed multiplication with initialized temporaries, not MUL. No claim of executing these programs or a speedup is made by this design deliverable.

### 8.2 Physical implementation boundary

Physical top is the enabled `nebula_cpu_npu_top`; its netlist contains CPU logic, the specified GPR storage, stage/CSR/protocol state and NPU logic. Program/data memories and their bus models are external. The initial target is Sky130HD standard cells, library corner `tt_025C_1v80`, nominal 25 C and 1.80 V, one 100-ns clock (10-MHz target) applied to clk. This is a constraint and corner selection, not achieved timing. rst_n and the synchronous external port protocols are preserved; no internal generated-clock interface or additional pin is required.

External-memory timing is a functional bus contract, not a characterized SRAM macro. The physical designer must apply and report actual input/output timing assumptions, reset treatment, loads and uncertainty using available physical collateral, rather than invent package/pad/memory delays or claim them measured. Report unconstrained paths and assumptions with STA; do not pretend the stated period alone constrains every off-chip path. Produce reproducible physical reports and STA/DRC/LVS evidence for the applicable digital flow, with consistent top/source/configuration and corner. Measured area, power, delay, route quality and software cycles require actual evidence; none is supplied here.

No pads, package, SRAM macro, foundry authorization, silicon fabrication, official RISC-V certification or additional hardware scope is included. ACT4 passing only establishes the applicable locked subset; it is not certification. PPA ranking and any physical success verdict require later real implementation/check results.

## 9. Frozen acceptance and performance accounting

All nine `spec/acceptance.json` check classes remain mandatory: base_isa_csr_traps, pipeline_timing, memory_wait_reset, npu_signed_dot4, npu_latency_backpressure_reset_kill, extension_commit_and_hazards, operator_exact_outputs, physical_sta_drc_lvs, independent_reproduction. Checkers are immutable. Designers generate fresh original synthesizable RTL; they must not inspect/copy evaluator reference CPU, prior candidates or private answers and must not weaken tests to pass.

Port_timing_v1 (2026-10-09) requires: contiguous 64 independent ADDI fetches and retirements, per-instruction n+4; zero added ordinary ALU dependency bubbles without bus waits/control flow; dependent load-use delta <=1 cycle under identical bus timing; and each fixed no-control-flow microprogram's total retirement span no larger than its frozen budget under each of the three frozen bus conditions. These are acceptance obligations, not optional optimizations. Branch/JAL/JALR penalties are measured/reported without inventing an upper bound. Historical results do not establish success under the newer timing/scoring version.

Define span S = last normal-retirement edge - first normal-retirement edge for a straight-line program of N retired instructions. Pipeline fill is excluded from S, but all gaps between these events count. For the no-wait independent ADDI/ordinary ALU stream S=N-1 exactly. For a same-timing dependent ALU counterpart, S is unchanged. For load-use pairs, compare both complete retirement spans with the identical request-ready/response schedule; each isolated dependency may contribute at most one cycle. No duplicated ready wait, repeated request, redundant response-collection stage, whole-pipeline drain/restart, register-file access bubble or extra retirement serialization is allowed to hide in both variants.

For memory sequences, an accepted memory token enters EX/MEM at a, completes a response handshake at s>=a+1, enters MEM/WB at s and retires at s+1. Request-ready waits before a and response waits beyond the earliest legal s are explicit bus waits. With EX-to-MEM request eligibility and one-cycle response handshake availability, a memory token needs no intrinsic extra MEM cycle; a longer external response holds the token only for the actual waiting interval. This supplies the timing model for span comparison; arithmetic stages retain unit throughput, and an independent instruction immediately following a memory wait resumes without an extra drain/fill penalty. Consecutive memory requests are serialized by the single-owner protocol and reuse a safe completion boundary as described in section 5. No algebraic bound alone is advertised as a pass of unprovided numerical tests.

The missing `acceptance.md` is referenced by both copies of the base contract. Neither the immutable inline payload nor acceptance.json nor public_cpu_tb.sv nor run_smoke.py contains its exact microprogram lengths, span limits, or three ready/response conditions. The public CPU test only exercises the 64 ADDIs; NPU smoke covers 64 signed vectors, response timing, response holding, reset and kill; integration smoke is lint only. None proves full ISA correctness, span budgets, operator software correctness or physical closure. The designer must retain the obligations above, and the architecture sign-off item is to obtain the frozen plan and match every budget/condition explicitly before reporting full closure. It is not permissible to reinterpret absent values as unlimited, infer full acceptance from smoke, or fabricate a pass.

Preserve scoring `t09_group_cycles10_v1`: raw 75 points scale by 50/75 to functional 50; original functional subitems scale proportionally to a total 40 and the independent cycle group contributes 10. Original F=48: integer/control 20; endian/byte enables/memory/sign extension 12; CSR/exceptions/MRET 8; applicable locked ACT4 8. Original P=27: hazard functional results 4.8; random waits/backpressure 4; flushing/precise commit/fetch-retire gate 3.2; cycle checks 15. The fixed 22 cycle checks earn normalized 10 if all 22 pass, 5 for 11–21, and 0 for 0–10. Safety failures still zero their affected subitem. Do not deduct 5 repeatedly per failed cycle item or count cycle failures again in hazard/latency scoring. Functional full 50 is required to unlock PPA (maximum 50) and time (maximum 5). Fetch-retire gating is not itself PPA ranking. Report scoring version with any historical results.

Frozen development resources remain 16 vCPU, 32 GiB RAM, 100 GiB writable disk, two hours and at most 1.2 million same-model tokens. The missing plan also owns detailed program suites, differential strategies, timeouts and pass conditions; these cannot be fabricated by this design. No smoke/ACT4/STA/DRC/LVS/software runtime was executed in this document-only task.

## 10. Traceability and sign-off

Each local requirement group below maps to the entire corresponding source clause, including normative Appendix A. The absence of a released ledger is not permission to omit requirements.

| Local ID | Frozen requirement group | Design closure/evidence obligation |
|---|---|---|
| D01 | Complete immutable source, released classification, original RTL, no private/reference copying | Provenance and sections 1, 9; full source appendix |
| D02 | Default/optional ENABLE_XNEBULA, explicit generate, unchanged base contract | Sections 1, 3, 7 |
| D03 | Complete public CPU and enabled wrapper ports | Section 2.1, 27 exact ports |
| D04 | Complete standalone NPU ports | Section 2.2, 10 exact ports |
| D05 | Five true stages, four independent boundary registers | Section 4.1–4.2, data/control ownership |
| D06 | Full RV32I integer/control/load/store/LUI/AUIPC ISA, x0 | Section 3, section 5 lanes |
| D07 | Unsupported extensions, no MMU/cache/interrupt/OS/predictor/generic mul-div | Sections 1, 3 |
| D08 | FENCE ordered no-op, FENCE.I illegal | Sections 3, 6 |
| D09 | Reset PC, CSR reset, common memory/NPU reset, in-flight clearing | Sections 2, 3, 5, 6, 7 |
| D10 | Fixed one-cycle ordered instruction memory, invalid/wrong-path returns | Sections 4.1, 4.3, 5.1 |
| D11 | One outstanding data request, ready/response backpressure, 1–8 cycles | Section 5.2 |
| D12 | Word-addressed bus, byte lanes, endian/sign extension, alignment before request | Section 5.3 |
| D13 | External 256-KiB image and external tohost semantics | Section 5.4 |
| D14 | Precise exceptions, exact causes/PC/tval, no fault effects | Section 6.1, sections 4.3, 5.2–5.3 |
| D15 | Exact CSR range, masking, read-only legality, source-zero distinctions | Section 6.2 |
| D16 | Trap mstatus transitions/direct mtvec and MRET | Section 6.1–6.2 |
| D17 | One real ordered WB commit, independent trap outputs, no trace collector | Sections 2.1, 4.2, 6.3 |
| D18 | Exact n+4 and continuous 64-ADDI fetch/retire, no fake stages | Section 4.2, section 9 |
| D19 | Forwarding, ordinary ALU zero bubbles, x0/dual/one-gap cases | Section 4.4 |
| D20 | Load-use delta <=1, actual bus waits separate | Sections 4.4, 5.2, 9 |
| D21 | Frozen total retirement-span budgets and three bus conditions | Section 9; OPEN until absent acceptance.md is supplied |
| D22 | Branch/jump flush and penalties reported without new bound | Sections 3, 4.3, 9 |
| D23 | xdot4 exact encoding/legality and disabled custom-0 trap | Sections 1, 3, 7.1 |
| D24 | Signed four parallel products, widened reduction, lane0 low byte | Section 7.1 |
| D25 | NPU n+2 result, single outstanding, held response | Section 7.2 |
| D26 | Reset/kill priority, all phases canceled, no hidden effects | Sections 7.2–7.3 |
| D27 | Extension operand hazards, younger waits, normal WB, exactly one retirement | Section 7.3 and section 4.4 |
| D28 | Enabled top, external memories, ordered manifests/lock | Sections 1, 2, 8.2 |
| D29 | Sky130HD tt_025C_1v80, 100ns, physical evidence/no fabricated claims | Section 8.2 |
| D30 | DOT64, signed GEMM8, CONV3, INT32 CPU accumulation without M | Section 8.1 |
| D31 | Immutable independent checker, all acceptance check groups/reproduction | Section 9 and Appendix B |
| D32 | Locked ISA/privilege and ACT4 scope, no official-certification claim | Sections 3, 6, 8.2, 9 and normative source appendix |
| D33 | Frozen resources, scoring, historical-version limits | Section 9 and normative source appendix |

Design consistency checks for subsequent implementation review are: exact port equality for core/top; four boundary groups and the n..n+4 table reflected by actual writes; exclusive commit/trap; no invalid/excepting producer forwarding; no alignment-fault bus request; accepted/completed/outstanding conservation <=1 on each handshake interface; cancellation priority at every NPU phase; stable blocked request/response payloads; response capture followed by normal MEM/WB/WB; and independent expected software results. These checks are specifications for real verification, not assertions that RTL or physical checks passed.

Unresolved design/sign-off items: **D21 — obtain the frozen acceptance.md numerical span budgets, exact microprograms and three bus timing conditions (including edge conventions), plus its referenced detailed acceptance parameters; verify the architecture against them.** All other supplied behavioral clauses are expanded above. No imaginary measurements are included. Implementation and measurement verification remain future delivery work, distinct from this missing specification item.

## Appendix A. Complete immutable CPU/NPU source, preserved verbatim

The following source text is normative. Its internal references are source references; the absent acceptance.md is tracked explicitly above.

# CPU/NPU case design contract v1

This is a detailed engineering input authorized by the project owner. Preserve the complete frozen T09 contract in t09-base-contract.md. CPU ports and public top module are those of public_cpu_tb.sv. Generate fresh original synthesizable RTL; do not inspect/copy the evaluator reference CPU, prior candidates, or private answer material.

CPU module rv32i_five_stage_cpu has parameter ENABLE_XNEBULA=0. Default 0 must satisfy the unmodified base contract. When 1 it instantiates nebula_npu_dot4 inside an explicit generate block and implements xdot4. Preserve five real pipeline stages and exact base fetch-to-retire timing.

NPU module nebula_npu_dot4 ports: input clk,rst_n,req_valid; output req_ready; input [31:0] req_a,req_b; output rsp_valid; input rsp_ready; output [31:0] rsp_data; input kill. Four parallel signed 8-bit products with widened signed reduction; lower byte is lane0. Accept at edge n when valid&ready; valid output after edge n+2. At most one operation outstanding; response and data stable until consumed. reset and kill cancel all work and dominate acceptance/response. No hidden accumulator/saturation/memory side effects.

xdot4 rd,rs1,rs2 is R type opcode 0x0b funct3=0 funct7=0; returns signed INT32 sum of four signed INT8 products. Invalid extension encodings trap. rd=x0 discards write but still retires. Operands obey forwarding and load-use rules. Younger work stalls during NPU wait; killed or wrong-path instructions cannot write or retire. Exactly one commit per valid instruction. When disabled all custom-0 opcodes trap. NPU response must enter normal pipeline writeback, not fake commit delays.

Top nebula_cpu_npu_top has exactly the same external port list as rv32i_five_stage_cpu; it instantiates core with ENABLE_XNEBULA=1. Memory remains external to the physical boundary. Supply integration/design.f and dependencies.lock.json with explicit ordered files, top and configuration.

Initial physical condition Sky130HD tt_025C_1v80 and clock 100ns. No pads, package, SRAM macro, foundry authorization or fabricated-silicon claims.

Programs: DOT64, signed INT8 GEMM8, CONV3 (8x8 input,3x3 valid kernel). Result INT32, normal CPU ADD accumulation; no M extension. Independent checker remains immutable; do not weaken it to obtain a pass.

## Base CPU contract

# T09 · RV32I 五级流水线 CPU

**设计需求**：单发射、顺序提交、32-bit RV32I 指令，明确分开的 IF/ID、ID/EX、EX/MEM、MEM/WB 四组级间寄存器；不允许以单指令多周期控制器冒充五级流水线。支持 RV32I 全部整数算术、逻辑、移位、分支、跳转、字节/半字/字访存、LUI/AUIPC、FENCE、ECALL、EBREAK；另支持 Zicsr 六种 CSR 操作及 MRET。无 M/A/F/D/C、无 MMU/缓存/中断，只有 M-mode。取指地址和访存地址按 ISA 要求检查对齐；不支持非对齐访存。`x0` 恒为 0。JALR 清目标 bit0。`FENCE` 对本题有序、一次一笔的数据端口无额外可见动作；`FENCE.I` 不支持并触发非法指令异常。

**复位与总线**：`clk,rst_n`，复位 PC=`0x8000_0000`。指令端 `imem_valid,imem_addr[31:0],imem_rdata[31:0]`；当周期的 `imem_valid/imem_addr` 在上升沿采样，下一周期给出对应 `imem_rdata`，每周期可接收一笔，响应严格顺序、无取指错误；没有前一周期有效请求时数据不验收。已发出的错误路径取指响应可以返回，但 CPU 必须丢弃。数据端 `dmem_req_valid,dmem_req_ready,dmem_req_write,dmem_req_addr[31:0],dmem_req_wdata[31:0],dmem_req_wstrb[3:0]` 与 `dmem_rsp_valid,dmem_rsp_ready,dmem_rsp_rdata[31:0],dmem_rsp_err`；每笔请求被接受后，在 1–8 周期内给一次保持型响应，单次只允许一笔未完成。数据端地址总是对齐的 32-bit word 地址：字节/半字访问由地址低位计算 byte lane、写掩码和放入对应 lane 的写数据；读响应返回完整 32-bit word，由 CPU 截取并符号扩展。非对齐访问须在发请求前报异常。错误响应表示该笔写入**没有内存副作用**。存储器与 CPU 一起复位，复位期间清空在途事务。指令、数据空间均指向外部 256 KiB 镜像；MMIO `0x8003_F000` 为 `tohost`，写入 1 表示程序通过，其余非零表示失败，CPU 不得硬编码此地址的行为。

**异常与 CSR**：非法指令、指令地址非对齐、load/store 非对齐、ECALL、EBREAK、数据端访问错误均为精确异常；faulting 指令不写回寄存器或内存，年轻指令全部冲刷。异常 `mcause` 编码：指令地址非对齐 0，非法指令 2，EBREAK 3，load 非对齐 4，load 访问错误 5，store 非对齐 6，store 访问错误 7，M-mode ECALL 11。若同一指令可能触发多个原因，先做地址对齐检查，再发总线请求，因此非对齐优先于访问错误。`mepc` 保存 faulting 指令 PC；`mtval` 对地址类异常保存故障地址，对非法指令保存 32-bit 指令编码，对 ECALL/EBREAK 为 0。

**CSR 的确切范围**：`mstatus(0x300)` 仅 MIE(bit3)、MPIE(bit7)、MPP(bits12:11) 可见；本题只有 M-mode，MPP 恒为 `2'b11`。复位值 `0x0000_1800`。进入异常时 `MPIE←MIE,MIE←0,MPP←3`；MRET 时 `MIE←MPIE,MPIE←1,MPP←3,PC←mepc`。`mtvec(0x305)` 仅 direct 模式，写入值低两位强制 0，复位值 `0x8000_0000`。`mscratch(0x340)`、`mepc(0x341)`、`mcause(0x342)`、`mtval(0x343)` 可读写，除 `mepc` 低两位强制 0 外复位为 0；只读 `misa(0x301)=0x4000_0100`、`mhartid(0xF14)=0`。其他 CSR 地址和对只读 CSR 的写操作触发非法指令异常；CSRRS/CSRRC 的源为 x0、立即数形式源为 0 时不写 CSR。所有未列的 `mstatus` 位读 0、写忽略。异常/CSR 编码遵循锁定的[RISC-V ISA/特权规范](https://github.com/riscv/riscv-isa-manual)；ACT4 配置必须与本任务范围一致。

**提交观察口**：每条正常退休指令输出一个周期的 `commit_valid,commit_pc[31:0],commit_insn[31:0],commit_rd[4:0],commit_wdata[31:0],commit_mem_addr[31:0],commit_mem_wstrb[3:0],commit_mem_wdata[31:0]`；无寄存器写回时 `commit_rd=0`，无存储写时 `commit_mem_wstrb=0`。异常事件输出独立 `trap_valid,trap_pc[31:0],trap_cause[31:0],trap_tval[31:0]`，不计为正常退休。这些是 CPU RTL 的轻量退休观察端口，供评测方自行采样；Agent **不需**生成 trace 文件或编写 trace 采集器。观察口只用于验收，不得成为执行功能的输入。

**取指至退休延时与资源边界**：寄存器文件仅 32×32 bit；程序/数据存储器均在核外。零等待、无相关的连续 64 条 ADDI 程序中，逐条记录取指请求被采样的上升沿 `n`；该指令须在 `n+4` 上升沿之后的稳定观察点输出 `commit_valid` 和对应 `commit_pc`。这表示从 IF 请求到 WB 观察跨越四个完整周期、经过 `n..n+4` 五个边沿；响应按本题一周期指令存储器时序提供。不得靠延迟 `commit_valid` 伪造流水级，后级的寄存器写回和存储器副作用也必须与提交轨迹一致。本门禁不作为 PPA 排名。实现须提供必要的旁路、load-use 停顿、分支/跳转冲刷、数据端等待停顿。无分支预测器、缓存、乘除法器或操作系统。

**周期性能补充（port_timing_v1，2026-10-09）**：上述 64 条无相关 ADDI 的取指与退休必须分别连续、稳态每拍一条，逐条 `n+4` 延时要求仍保留。无总线等待、无控制转移的普通 ALU 数据相关（紧邻、隔一条、双源、x0）不得因前递额外插入气泡；load-use 相比相同总线时序的无相关对照最多增加一拍，外部 ready/response 等待另计。验收另外固定无控制流微程序的总退休跨度上限，防止相关/无相关版本共同插入额外气泡而抵消差值；具体预算与三种总线条件见[CPU 验收计划](acceptance.md)。分支/JAL/JALR 罚拍仅报告，不新增未约定的上限。此补充明确了旧检查未覆盖、部分此前未量化的性能约束；历史成绩不冒充新版通过，参考 RTL 与候选使用同一规则。

**资源与时限**：16 vCPU、32 GiB RAM、100 GiB 可写盘；开发时限 2 小时，同模型 token 上限 120 万。

**验收权重（t09_group_cycles10_v1）**：75 点按 `50/75` 归一为功能 50 分；原有功能子项按原比例缩放至合计 40 分，独立周期检查组占 10 分。原始 F=48：整数与控制流 20；大小端/字节使能、访存与符号扩展 12；CSR/异常/MRET 8；锁定配置的 ACT4 适用测试 8。原始 P=27：数据相关的功能结果 4.8；随机数据等待及背压 4；冲刷、精确提交和取指至退休延时门禁 3.2；独立周期检查 15。周期组固定 22 项：22 项全过得归一化 10 分，通过 11–21 项得 5 分，通过 0–10 项得 0 分；安全缺陷仍按通用规则使所在子项为 0。不逐项累计扣 5 分，也不将周期失败再次并入原 hazard/latency 组。功能部分仍须满 50 分才启用 PPA（满分 50）和时间分（满分 5）。详细程序集、差分策略、超时与通过条件见[CPU 验收计划](acceptance.md)。ACT4 子集通过不等于 RISC-V 官方认证；历史成绩须区分评分版本。


## Appendix B. Complete immutable acceptance JSON

```json
{
  "schema_version": 1,
  "scope": "RV32I five-stage CPU plus Xnebula xdot4",
  "base_contract": "t09-base-contract.md",
  "checks": [
    "base_isa_csr_traps",
    "pipeline_timing",
    "memory_wait_reset",
    "npu_signed_dot4",
    "npu_latency_backpressure_reset_kill",
    "extension_commit_and_hazards",
    "operator_exact_outputs",
    "physical_sta_drc_lvs",
    "independent_reproduction"
  ],
  "immutable_checker": true
}

```
