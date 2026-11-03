"""Freeze CPU + accelerator traffic harness around the B-family memory DUT."""
from __future__ import annotations

import json
import random
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from study_protocol import digest, write_json
from study_portability import case_root

ROOT = Path(__file__).resolve().parents[1]
CASE = case_root(ROOT)
sys.path.append(str(CASE/"scripts"))
from kernel_programs import Program, SIZE, TOHOST, BASE


def shell():
    old=(CASE/"released_design/rtl/integration/nebula_cpu_npu_top.sv").read_text()
    header=old[:old.index("    rv32i_five_stage_cpu")]
    header=header.replace("\n);", """,
    output logic [1:0] dmem_req_tag,
    input logic [1:0] dmem_rsp_tag,
    output logic accelerator_done, accelerator_error,
    output logic [31:0] accelerator_checksum
);""")
    cpu_ports=["clk","rst_n","imem_valid","imem_addr","imem_rdata",
               "commit_valid","commit_pc","commit_insn","commit_rd","commit_wdata",
               "commit_mem_addr","commit_mem_wstrb","commit_mem_wdata",
               "trap_valid","trap_pc","trap_cause","trap_tval"]
    bus=dict(req_valid="req_valid[0]",req_ready="req_ready[0]",req_write="req_write[0]",
             req_addr="req_addr[31:0]",req_wdata="req_wdata[31:0]",req_wstrb="req_wstrb[3:0]",
             rsp_valid="rsp_valid[0]",rsp_ready="rsp_ready[0]",
             rsp_rdata="rsp_rdata[31:0]",rsp_err="rsp_err[0]")
    connections=[f".{p}({p})" for p in cpu_ports]+[f".dmem_{p}({v})" for p,v in bus.items()]
    return header+"""
 logic [1:0] req_valid,req_ready,req_write,rsp_valid,rsp_ready,rsp_err;
 logic [63:0] req_addr,req_wdata,rsp_rdata;
 logic [7:0] req_wstrb;
 logic [15:0] req_id,rsp_id;
 logic [7:0] issued,received;
 // Fixed neighboring harness: up to four independent read requests, in-order
 // checksummed responses. It stresses an accelerator port, not a new NPU ISA.
 assign req_valid[1]=rst_n && issued<64 && (issued-received)<4;
 assign req_write[1]=0;assign req_wdata[63:32]=0;assign req_wstrb[7:4]=0;
 assign req_addr[63:32]=32'h80018000+{22'b0,issued,2'b0};
 assign req_id={issued,8'b0};assign rsp_ready[1]=rst_n;
 assign accelerator_done=received==64;
 always_ff @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin issued<=0;received<=0;accelerator_checksum<=0;accelerator_error<=0;end
  else begin
   if(req_valid[1] && req_ready[1])issued<=issued+1;
   if(rsp_valid[1] && rsp_ready[1])begin
    received<=received+1;accelerator_checksum<=accelerator_checksum+rsp_rdata[63:32];
    if(rsp_id[15:8]!=received || rsp_err[1])accelerator_error<=1;
   end
  end
 end
 capacity_memory shared_memory(.clk(clk),.rst_n(rst_n),.flush(1'b0),
  .req_valid(req_valid),.req_ready(req_ready),.req_write(req_write),
  .req_addr(req_addr),.req_wdata(req_wdata),.req_wstrb(req_wstrb),.req_id(req_id),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_rdata(rsp_rdata),.rsp_id(rsp_id),.rsp_err(rsp_err),
  .m_req_valid(dmem_req_valid),.m_req_ready(dmem_req_ready),.m_req_write(dmem_req_write),
  .m_req_addr(dmem_req_addr),.m_req_wdata(dmem_req_wdata),.m_req_wstrb(dmem_req_wstrb),
  .m_req_tag(dmem_req_tag),.m_rsp_valid(dmem_rsp_valid),.m_rsp_ready(dmem_rsp_ready),
  .m_rsp_tag(dmem_rsp_tag),.m_rsp_rdata(dmem_rsp_rdata),.m_rsp_err(dmem_rsp_err));
 rv32i_five_stage_cpu #(.ENABLE_XNEBULA(1'b1)) core(
 """+",\n ".join(connections)+");\nendmodule\n"


def firmware(words,seed):
    rng=random.Random(seed)
    p=Program();p.li(1,0x80010000)
    expected=[]
    for i in range(words):
        value=rng.getrandbits(32);expected.append(value)
        p.li(2,value);p.sw(2,1,4*i);p.i("lw",3,1,4*i)
        p.branch("bne",2,3,"failure")
    p.li(6,TOHOST);p.li(7,1);p.sw(7,6)
    p.label("halt");p.jump("halt")
    p.label("failure");p.li(6,TOHOST);p.li(7,3);p.sw(7,6);p.jump("halt")
    image=bytearray(SIZE);code=p.finish();image[:len(code)]=code
    accelerator=[rng.getrandbits(32) for _ in range(64)]
    for i,v in enumerate(accelerator):
        struct.pack_into("<I",image,0x18000+4*i,v)
    return p,image,dict(cpu_words=words,seed=seed,cpu_expected=expected,
                       accelerator_expected_checksum=sum(accelerator)&0xffffffff,
                       useful_transactions=2*words+64,
                       oracle="Python memory values/checksum; self-checking RV32I loads/stores")


def bench():
    text=(CASE/"verification/tb_cpu_npu.sv").read_text()
    text=text.replace("  nebula_cpu_npu_top dut (.*);","""  logic [1:0] dmem_req_tag,dmem_rsp_tag;
  logic accelerator_done,accelerator_error;
  logic [31:0] accelerator_checksum,expected_checksum;
  bit queued_valid[0:3],queued_error[0:3];
  logic [31:0] queued_data[0:3];
  integer queued_delay[0:3],chosen_response,inflight,peak_inflight;
  nebula_cpu_npu_top dut (.*);""")
    start=text.index("    dmem_req_ready = !pending_response")
    end=text.index("    #2;",start)
    text=text[:start]+"""    if(!rst_n)for(int q=0;q<4;q++)queued_valid[q]=0;
    chosen_response=-1;inflight=0;
    for(int q=0;q<4;q++)begin
      if(queued_valid[q])inflight++;
      if(queued_valid[q] && queued_delay[q]==0)chosen_response=q;
    end
    if(inflight>peak_inflight)peak_inflight=inflight;
    dmem_req_ready=inflight<4 && cycle_count%3!=1;
    dmem_rsp_valid=chosen_response>=0;
    dmem_rsp_tag=chosen_response<0?0:chosen_response;
    dmem_rsp_rdata=chosen_response<0?0:queued_data[chosen_response];
    dmem_rsp_err=chosen_response<0?0:queued_error[chosen_response];
"""+text[end:]
    start=text.index("      pending_response = 1;")
    end=text.index("      if (dmem_req_write && !error_now)",start)
    text=text[:start]+"""      if(queued_valid[dmem_req_tag])$fatal(1,"tag reused while memory outstanding");
      queued_valid[dmem_req_tag]=1;queued_error[dmem_req_tag]=error_now;
      queued_data[dmem_req_tag]=error_now?0:dmem_req_write?0:read_word(dmem_req_addr);
      rng ^= rng << 13;rng ^= rng >> 17;rng ^= rng << 5;
      queued_delay[dmem_req_tag]=8+int'(rng%16);
      response_delay_mask|=1<<(queued_delay[dmem_req_tag]+1);
"""+text[end:]
    old="""    if (response_taken) pending_response = 0;
    else if (pending_response && response_delay > 0) response_delay--;"""
    assert old in text
    text=text.replace(old,"""    if(response_taken)queued_valid[chosen_response]=0;
    for(int q=0;q<4;q++)if(queued_valid[q] && queued_delay[q]>0)queued_delay[q]--;""")
    text=text.replace('    $readmemh(image_file, memory);',"""    $readmemh(image_file, memory);
    expected_checksum=0;peak_inflight=0;
    for(int q=0;q<4;q++)begin queued_valid[q]=0;queued_error[q]=0;queued_data[q]=0;queued_delay[q]=0;end
    for(int word_index=0;word_index<64;word_index++)
      expected_checksum+=read_word(32'h80018000+4*word_index);""",1)
    text=text.replace("if (host_written && host_committed) begin",
                      "if (host_written && host_committed && accelerator_done) begin")
    text=text.replace("    if (!passed)", """    if(accelerator_error || accelerator_checksum!==expected_checksum)
      $fatal(1,"accelerator checksum/order failed");
    $display("SHARED_MEMORY peak_outstanding=%0d checksum=%h",peak_inflight,accelerator_checksum);
    if (!passed)""")
    assert text.count("#2;")==3
    for delay in ("2.631","5.263","2.632"):
        text=text.replace("#2;",f"#{delay};",1)
    return text


def build(name):
    task=ROOT/"tasks"/name;out=ROOT/"integration"/name
    if out.exists():raise ValueError("Prior integration preserved")
    for directory in ("rtl/cpu","rtl/npu","rtl/integration","rtl/candidate","verification","workloads"):
        (out/directory).mkdir(parents=True)
    for relative in ("cpu/rv32i_five_stage_cpu.sv","npu/nebula_npu_dot4.sv"):
        shutil.copy2(CASE/"released_design/rtl"/relative,out/"rtl"/relative)
    (out/"rtl/integration/nebula_cpu_npu_top.sv").write_text(shell())
    shutil.copy2(task/"grader/reference.sv",out/"rtl/candidate/capacity_memory.sv")
    (out/"verification/tb_cpu_npu.sv").write_text(bench())
    workloads=[]
    for label,words,seed in (("short",16,8101),("mixed",32,8102),("long",64,8103)):
        folder=out/"workloads"/label;folder.mkdir()
        p,image,meta=firmware(words,seed)
        (folder/"memory.hex").write_text("".join(f"{b:02x}\n" for b in image))
        (folder/"program.S").write_text("\n".join(p.assembly)+"\n")
        write_json(folder/"workload.json",meta);workloads.append(dict(name=label,**meta))
    write_json(out/"freeze-draft.json",dict(task=name,period_ns=10.526,isa_modified=False,
        cpu_sha256=digest(out/"rtl/cpu/rv32i_five_stage_cpu.sv"),workloads=workloads,formal_frozen=False,
        scope="CPU plus fixed accelerator memory-traffic harness; original embedded NPU unchanged",
        source_sha256={str(p.relative_to(out)):digest(p) for p in out.rglob("*") if p.is_file()}))
    return out


def qualify(out):
    from build_capacity_dot_integration import qualify as shared_qualify
    result=shared_qualify(out)
    peaks=[]
    import re
    for logfile in (out/"qualification").glob("*-*.log"):
        match=re.search(r"peak_outstanding=(\d+)",logfile.read_text())
        if match:peaks.append(int(match[1]))
    result["peak_outstanding_observed"]=peaks
    result["scope"]="Self-checking CPU firmware and independent accelerator checksum/IDs; tagged, delayed memory responses"
    if out.name=="B2":
        result["passed"]=result["passed"] and bool(peaks) and max(peaks)==4
    write_json(out/"qualification/qualification.json",result)
    print(json.dumps(dict(task=out.name,passed=result["passed"],peaks=peaks)),flush=True)
    return result


if __name__=="__main__":
    for name in ("B1","B2"):
        if not qualify(build(name))["passed"]:raise SystemExit(1)
