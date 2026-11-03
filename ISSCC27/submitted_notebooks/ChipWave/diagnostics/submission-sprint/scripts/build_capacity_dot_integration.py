"""Frozen MMIO integration and self-checking RV32I firmware for A1/A2."""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

from study_protocol import digest, write_json
from study_portability import case_root

ROOT = Path(__file__).resolve().parents[1]
CASE = case_root(ROOT)
sys.path.append(str(CASE/"scripts"))
from kernel_programs import Program, SIZE, TOHOST

MMIO = 0x40000000


def shell():
    old = (CASE/"released_design/rtl/integration/nebula_cpu_npu_top.sv").read_text()
    header = old[:old.index("    rv32i_five_stage_cpu")]
    core_ports = [
        "clk", "rst_n", "imem_valid", "imem_addr", "imem_rdata",
        "commit_valid", "commit_pc", "commit_insn", "commit_rd", "commit_wdata",
        "commit_mem_addr", "commit_mem_wstrb", "commit_mem_wdata",
        "trap_valid", "trap_pc", "trap_cause", "trap_tval"]
    names = ("req_valid","req_ready","req_write","req_addr","req_wdata","req_wstrb",
             "rsp_valid","rsp_ready","rsp_rdata","rsp_err")
    connections = [f".{p}({p})" for p in core_ports]
    connections += [f".dmem_{p}(cpu_{p})" for p in names]
    return header + """
 logic cpu_req_valid,cpu_req_ready,cpu_req_write,cpu_rsp_valid,cpu_rsp_ready,cpu_rsp_err;
 logic [31:0] cpu_req_addr,cpu_req_wdata,cpu_rsp_rdata;
 logic [3:0] cpu_req_wstrb;
 logic selected,mmio_ready,mmio_pending,mmio_fire;
 logic [31:0] mmio_response,staged_a,staged_b;
 logic cmd_valid,cmd_ready,data_valid,data_ready,cancel_valid,rsp_valid,rsp_ready;
 logic [7:0] rsp_id;
 logic [31:0] rsp_data;
 wire [5:0] offset=cpu_req_addr[5:0];
 assign selected=cpu_req_addr[31:12]==20'h40000;
 assign cmd_valid=rst_n && selected && cpu_req_valid && !mmio_pending && cpu_req_write && offset==0;
 assign data_valid=rst_n && selected && cpu_req_valid && !mmio_pending && cpu_req_write && offset==12;
 assign cancel_valid=rst_n && selected && cpu_req_valid && !mmio_pending && cpu_req_write && offset==16;
 assign rsp_ready=rst_n && selected && cpu_req_valid && !mmio_pending && !cpu_req_write && offset==24;
 always_comb begin
  mmio_ready=1;
  if(cpu_req_write && offset==0)mmio_ready=cmd_ready;
  if(cpu_req_write && offset==12)mmio_ready=data_ready;
  if(!cpu_req_write && offset==24)mmio_ready=rsp_valid;
 end
 assign cpu_req_ready=rst_n && !mmio_pending && (selected?mmio_ready:dmem_req_ready);
 assign dmem_req_valid=rst_n && !mmio_pending && !selected && cpu_req_valid;
 assign dmem_req_write=cpu_req_write;assign dmem_req_addr=cpu_req_addr;
 assign dmem_req_wdata=cpu_req_wdata;assign dmem_req_wstrb=cpu_req_wstrb;
 assign dmem_rsp_ready=cpu_rsp_ready && !mmio_pending;
 assign cpu_rsp_valid=mmio_pending || dmem_rsp_valid;
 assign cpu_rsp_rdata=mmio_pending?mmio_response:dmem_rsp_rdata;
 assign cpu_rsp_err=mmio_pending?1'b0:dmem_rsp_err;
 assign mmio_fire=selected && cpu_req_valid && cpu_req_ready;
 always_ff @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin mmio_pending<=0;mmio_response<=0;staged_a<=0;staged_b<=0;end
  else begin
   if(mmio_pending && cpu_rsp_ready)mmio_pending<=0;
   if(mmio_fire)begin
    mmio_pending<=1;mmio_response<=0;
    if(cpu_req_write)begin
     if(offset==4)staged_a<=cpu_req_wdata;
     if(offset==8)staged_b<=cpu_req_wdata;
    end else begin
     if(offset==20)mmio_response<={30'b0,cmd_ready,rsp_valid};
     if(offset==24)mmio_response<=rsp_data;
     if(offset==28)mmio_response<={24'b0,rsp_id};
    end
   end
  end
 end
 capacity_dot accelerator(.clk(clk),.rst_n(rst_n),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_id(cpu_req_wdata[7:0]),.cmd_len(cpu_req_wdata[14:8]),
  .data_valid(data_valid),.data_ready(data_ready),.data_id(cpu_req_wdata[7:0]),.data_a(staged_a),.data_b(staged_b),
  .cancel_valid(cancel_valid),.cancel_id(cpu_req_wdata[7:0]),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_id(rsp_id),.rsp_data(rsp_data));
 rv32i_five_stage_cpu #(.ENABLE_XNEBULA(1'b1)) core(
 """ + ",\n ".join(connections) + ");\nendmodule\n"


def firmware(depth, lengths, seed):
    rng = random.Random(seed)
    p = Program()
    p.li(1, MMIO)
    expected = []
    vectors = []
    for index, length in enumerate(lengths):
        a, b = [[rng.randrange(-128,128) for _ in range(length)] for _ in range(2)]
        vectors.append((a,b))
        expected.append(sum(x*y for x,y in zip(a,b)))

    def write(offset, value):
        p.li(2,value)
        p.sw(2,1,offset)

    for start in range(0, len(lengths), depth):
        end = min(start+depth, len(lengths))
        for index in range(start, end):
            write(0, ((index+1)&255) | (lengths[index]<<8))
        for index in range(start, end):
            a,b = vectors[index]
            for offset in range(0,len(a),4):
                for reg,v in ((4,a),(8,b)):
                    packed=sum(((v[offset+k] if offset+k<len(v) else 127)&255)<<(8*k) for k in range(4))
                    write(reg,packed)
                write(12,index+1)
        for index in range(start, end):
            label=f"poll_{index}"
            p.label(label)
            p.i("lw",3,1,20)
            p.i("andi",3,3,1)
            p.branch("beq",3,0,label)
            p.i("lw",4,1,28)
            p.li(5,index+1)
            p.branch("bne",4,5,"failure")
            p.i("lw",4,1,24)
            p.li(5,expected[index])
            p.branch("bne",4,5,"failure")
    p.li(6,TOHOST);p.li(7,1);p.sw(7,6)
    p.label("halt");p.jump("halt")
    p.label("failure");p.li(6,TOHOST);p.li(7,3);p.sw(7,6);p.jump("halt")
    image=bytearray(SIZE)
    code=p.finish()
    image[:len(code)]=code
    return p,image,dict(lengths=lengths,seed=seed,expected=expected,useful_macs=sum(lengths),
                        oracle="Python signed integer arithmetic, firmware checks IDs/results")


def build(task_name):
    depth=1 if task_name=="A1" else 4
    task=ROOT/"tasks"/task_name
    out=ROOT/"integration"/task_name
    if out.exists():
        raise ValueError("Existing integration revision is preserved")
    for name in ("rtl/cpu","rtl/npu","rtl/integration","rtl/candidate","verification","workloads"):
        (out/name).mkdir(parents=True)
    for relative in ("cpu/rv32i_five_stage_cpu.sv","npu/nebula_npu_dot4.sv"):
        shutil.copy2(CASE/"released_design/rtl"/relative,out/"rtl"/relative)
    (out/"rtl/integration/nebula_cpu_npu_top.sv").write_text(shell())
    shutil.copy2(task/"grader/reference.sv",out/"rtl/candidate/capacity_dot.sv")
    tb=(CASE/"verification/tb_cpu_npu.sv").read_text()
    needle="if (commit_mem_wstrb != 0) begin"
    assert tb.count(needle)==1
    # MMIO is internal: external-bus store receipts cannot observe those stores.
    tb=tb.replace(needle,"if (commit_mem_wstrb != 0 && commit_mem_addr[31:12] != 20'h40000) begin")
    assert tb.count("#2;")==3
    for delay in ("2.631","5.263","2.632"):
        tb=tb.replace("#2;",f"#{delay};",1)
    (out/"verification/tb_cpu_npu.sv").write_text(tb)
    workload_rows=[]
    for name,lengths,seed in (("short",[1,2,3,4],7301),("mixed",[5,7,31,63],7302),
                              ("long",[64,64,64,64],7303)):
        folder=out/"workloads"/name;folder.mkdir()
        p,image,meta=firmware(depth,lengths,seed)
        (folder/"memory.hex").write_text("".join(f"{byte:02x}\n" for byte in image))
        (folder/"program.S").write_text("\n".join(p.assembly)+"\n")
        write_json(folder/"workload.json",meta)
        workload_rows.append(dict(name=name,**meta))
    write_json(out/"freeze-draft.json",dict(task=task_name,period_ns=10.526,isa_modified=False,
        cpu_sha256=digest(out/"rtl/cpu/rv32i_five_stage_cpu.sv"),
        mmio_base=hex(MMIO),workloads=workload_rows,formal_frozen=False,
        scope="New MMIO shell; original CPU and embedded XNEBULA unit preserved",
        source_sha256={str(p.relative_to(out)):digest(p) for p in out.rglob("*") if p.is_file()}))
    return out


def qualify(out, *, seeds=(17,37,20261021), deadline=None):
    from capacity_process import remaining,run_group
    obj=out/"qualification/obj";obj.parent.mkdir()
    sources=sorted((out/"rtl").rglob("*.sv"))
    cmd=["verilator","--binary","--timing","--assert","-Wno-fatal","-j","2",
         "--top-module","tb_cpu_elf","--Mdir",str(obj),*map(str,sources),str(out/"verification/tb_cpu_npu.sv")]
    completed=run_group(cmd,text=True,capture_output=True,timeout=remaining(deadline,600))
    (obj.parent/"compile.log").write_text(completed.stdout+completed.stderr)
    if completed.returncode:
        report=dict(passed=False,compiled=False,rows=[],physical_qualified=False,
                    failure_class='candidate_integration_compile',exit_code=completed.returncode)
        write_json(obj.parent/"qualification.json",report)
        return report
    rows=[]
    for workload in ("short","mixed","long"):
        for seed in seeds:
            trace=obj.parent/f"{workload}-{seed}.jsonl"
            result=run_group([str(obj/"Vtb_cpu_elf"),f"+IMAGE={out/'workloads'/workload/'memory.hex'}",
                f"+TRACE={trace}",f"+SEED={seed}","+MAX_CYCLES=200000"],text=True,capture_output=True,timeout=remaining(deadline,120))
            (obj.parent/f"{workload}-{seed}.log").write_text(result.stdout+result.stderr)
            passed=result.returncode==0 and "CPU_ELF_PASS" in result.stdout
            rows.append(dict(workload=workload,memory_response_seed=seed,passed=passed))
            if not passed:
                break
        if not rows[-1]["passed"]:
            break
    report=dict(passed=len(rows)==3*len(seeds) and all(r["passed"] for r in rows),rows=rows,
                scope="Self-checking firmware arithmetic/IDs and external memory/commit consistency; not full new-firmware ISA differential",
                physical_qualified=False)
    write_json(obj.parent/"qualification.json",report)
    print(json.dumps(dict(task=out.name,**report)),flush=True)
    return report


if __name__=="__main__":
    for name in ("A1","A2"):
        result=qualify(build(name))
        if not result["passed"]:
            raise SystemExit(1)
