`timescale 1ns/1ps
module custom_traps_tb #(parameter bit ENABLE=1);
  localparam logic[31:0] BASE=32'h80000000;
  logic clk=0,rst_n=0;
  logic imem_valid;
  logic[31:0] imem_addr,imem_rdata=32'h13;
  logic dmem_req_valid,dmem_req_ready=1,dmem_req_write;
  logic[31:0] dmem_req_addr,dmem_req_wdata;
  logic[3:0] dmem_req_wstrb;
  logic dmem_rsp_valid=0,dmem_rsp_ready;
  logic[31:0] dmem_rsp_rdata=0;
  logic dmem_rsp_err=0,commit_valid,trap_valid;
  logic[31:0] commit_pc,commit_insn,commit_wdata;
  logic[4:0] commit_rd;
  logic[31:0] commit_mem_addr,commit_mem_wdata;
  logic[3:0] commit_mem_wstrb;
  logic[31:0] trap_pc,trap_cause,trap_tval;
  logic[31:0] bad_instruction;
  integer commits,cases=0;
  rv32i_five_stage_cpu #(.ENABLE_XNEBULA(ENABLE)) dut(.*);
  task automatic step;
    logic[31:0] instruction;
    instruction=32'h13;
    #2;
    if(rst_n&&imem_valid)case(imem_addr)
      BASE:instruction=32'h02500293; // addi x5,x0,37: older instruction must retire.
      BASE+4:instruction=bad_instruction;
      BASE+8:instruction=32'h00502023; // younger store must never reach the bus.
      default:instruction=32'h13;
    endcase
    if(rst_n&&dmem_req_valid)$fatal(1,"younger memory side effect before precise trap");
    clk=1;#2;imem_rdata=instruction;
    if(!rst_n&&(commit_valid||trap_valid))$fatal(1,"reset observation leak");
    if(rst_n&&commit_valid)begin
      if(commit_pc!==BASE||commit_insn!==32'h02500293||commit_rd!==5||commit_wdata!==37||commit_mem_wstrb!==0)
        $fatal(1,"invalid retirement before illegal custom trap pc=%h insn=%h",commit_pc,commit_insn);
      commits++;
    end
    clk=0;#2;
  endtask
  task automatic check(input logic[31:0] insn);
    bit caught;
    rst_n=0;imem_rdata=32'h13;commits=0;bad_instruction=insn;
    step();step();rst_n=1;caught=0;
    for(integer n=0;n<100;n++)begin
      step();
      if(trap_valid)begin
        if(trap_pc!==BASE+4||trap_cause!==2||trap_tval!==insn||commits!=1)
          $fatal(1,"custom trap mismatch pc=%h cause=%h tval=%h commits=%0d",trap_pc,trap_cause,trap_tval,commits);
        caught=1;break;
      end
    end
    if(!caught)$fatal(1,"custom trap timeout insn=%h",insn);
    cases++;
  endtask
  initial begin
    if(!ENABLE)check(32'h00b5028b); // valid extension encoding is illegal in base configuration.
    for(integer f3=1;f3<8;f3++)check(32'(f3)<<12|32'h00b5028b);
    for(integer f7=1;f7<128;f7++)check(32'(f7)<<25|32'h00b5028b);
    $display("CUSTOM_TRAPS_PASS enabled=%0d cases=%0d",ENABLE,cases);$finish;
  end
  initial begin #1000000;$fatal(1,"custom trap suite timeout");end
endmodule
