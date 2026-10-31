`timescale 1ns/1ps
module precise_custom_tb;
  localparam logic[31:0] BASE=32'h80000000, BAD=32'h20000000;
  logic clk=0,rst_n=0,imem_valid;
  logic[31:0] imem_addr,imem_rdata=32'h13;
  logic dmem_req_valid,dmem_req_ready=1,dmem_req_write;
  logic[31:0] dmem_req_addr,dmem_req_wdata;
  logic[3:0] dmem_req_wstrb;
  logic dmem_rsp_valid=0,dmem_rsp_ready;
  logic[31:0] dmem_rsp_rdata=0;
  logic dmem_rsp_err=1,commit_valid,trap_valid;
  logic[31:0] commit_pc,commit_insn,commit_wdata;
  logic[4:0] commit_rd;
  logic[31:0] commit_mem_addr,commit_mem_wdata;
  logic[3:0] commit_mem_wstrb;
  logic[31:0] trap_pc,trap_cause,trap_tval;
  integer mode,delay_setting,wait_count,commits,requests,cases=0;
  bit pending;
  nebula_cpu_npu_top dut(.*);
  function automatic logic[31:0] instruction(input logic[31:0] pc);
    case(pc)
      BASE:return 32'h20000537; // lui x10,0x20000: invalid external address.
      BASE+4:return 32'h010105b7; // lui x11,0x01010: packed lanes [0,0,1,1].
      BASE+8:return mode==2 ? 32'h00b5840b : mode==1 ? 32'h00b52023 : 32'h00052303;
      BASE+12:return mode==2 ? 32'h00052303 : 32'h00b5840b;
      BASE+16:return 32'h00b52023; // younger store must not issue.
      default:return 32'h13;
    endcase
  endfunction
  task automatic step;
    logic[31:0] next_instruction;
    bit accepted,taken;
    dmem_req_ready=!pending;
    dmem_rsp_valid=pending&&wait_count==0;
    #2;next_instruction=rst_n&&imem_valid?instruction(imem_addr):32'h13;
    accepted=rst_n&&dmem_req_valid&&dmem_req_ready;
    taken=rst_n&&dmem_rsp_valid&&dmem_rsp_ready;
    if(accepted)begin
      requests++;
      if(requests!=1||dmem_req_addr!==BAD||dmem_req_write!==(mode==1))
        $fatal(1,"unexpected/younger memory request mode=%0d",mode);
    end
    clk=1;#2;imem_rdata=next_instruction;
    if(!rst_n&&(commit_valid||trap_valid))$fatal(1,"reset observation leak");
    if(rst_n&&commit_valid)begin
      case(commits)
        0:if(commit_pc!==BASE||commit_rd!==10||commit_wdata!==BAD)$fatal(1,"older address retirement");
        1:if(commit_pc!==BASE+4||commit_rd!==11||commit_wdata!==32'h01010000)$fatal(1,"older operand retirement");
        2:if(mode!=2||commit_pc!==BASE+8||commit_rd!==8||commit_wdata!==2)$fatal(1,"older NPU retirement");
        default:$fatal(1,"faulting/younger instruction retired");
      endcase
      if(commit_mem_wstrb!==0)$fatal(1,"faulting/younger store committed");
      commits++;
    end
    clk=0;#2;
    if(taken)pending=0;
    else if(pending&&wait_count>0)wait_count--;
    if(accepted)begin pending=1;wait_count=delay_setting;end
  endtask
  task automatic check(input integer selected_mode,delay_cycles);
    bit caught;
    mode=selected_mode;delay_setting=delay_cycles;pending=0;wait_count=0;commits=0;requests=0;
    rst_n=0;imem_rdata=32'h13;step();step();rst_n=1;caught=0;
    for(integer n=0;n<150;n++)begin
      step();
      if(trap_valid)begin
        if(trap_pc!==(mode==2?BASE+12:BASE+8)||trap_cause!==(mode==1?7:5)||trap_tval!==BAD||
           commits!=(mode==2?3:2)||requests!=1)
          $fatal(1,"precise custom interaction mismatch mode=%0d delay=%0d pc=%h cause=%h commits=%0d",mode,delay_cycles,trap_pc,trap_cause,commits);
        caught=1;break;
      end
    end
    if(!caught)$fatal(1,"precise custom interaction timeout");
    cases++;
  endtask
  initial begin
    for(integer m=0;m<3;m++)for(integer d=0;d<8;d++)check(m,d);
    $display("PRECISE_CUSTOM_PASS cases=%0d",cases);$finish;
  end
  initial begin #1000000;$fatal(1,"precise custom timeout");end
endmodule
