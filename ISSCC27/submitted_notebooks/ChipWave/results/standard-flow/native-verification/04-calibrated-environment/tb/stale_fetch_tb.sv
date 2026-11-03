`timescale 1ns/1ps
module stale_fetch_tb #(parameter bit ENABLE=0);
  localparam logic [31:0] BASE=32'h80000000;
  logic clk=0,rst_n=0,imem_valid;
  logic [31:0] imem_addr,imem_rdata=32'h13;
  logic dmem_req_valid,dmem_req_ready=1,dmem_req_write;
  logic [31:0] dmem_req_addr,dmem_req_wdata;
  logic [3:0] dmem_req_wstrb;
  logic dmem_rsp_valid=0,dmem_rsp_ready;
  logic [31:0] dmem_rsp_rdata=0;
  logic dmem_rsp_err=0,commit_valid,trap_valid;
  logic [31:0] commit_pc,commit_insn,commit_wdata,commit_mem_addr,commit_mem_wdata;
  logic [4:0] commit_rd;
  logic [3:0] commit_mem_wstrb;
  logic [31:0] trap_pc,trap_cause,trap_tval;
  integer mode,commits,cases=0,serial_holds,redirect_fetches;
  logic [31:0] stale_word;
  bit expect_target;
  rv32i_five_stage_cpu #(.ENABLE_XNEBULA(ENABLE)) dut(.*);
  function automatic logic [31:0] instruction(input logic [31:0] pc);
    case(pc)
      BASE:return mode==2 ? 32'h00000097 : 32'h00100093;
      BASE+4:return mode==2 ? 32'h01108093 : 32'h00008093;
      BASE+8:return mode==2 ? 32'h00008267 : mode==1 ? 32'h0080026f : 32'h00108463;
      BASE+12:return 32'h00202023;
      BASE+16:return 32'h00200113;
      BASE+20:return 32'h340021f3;
      default:return 32'h13;
    endcase
  endfunction
  task automatic step;
    logic [31:0] word;
    bit redirect;
    #2;
    if(rst_n && expect_target)begin
      if(!imem_valid || imem_addr!==BASE+16)$fatal(1,"stale serial word blocked target fetch");
      redirect_fetches++;expect_target=0;
    end
    if(rst_n && dmem_req_valid)$fatal(1,"wrong-path store issued");
    if(rst_n && dut.if_v && dut.id_d.csr && (dut.ex_v||dut.mem_v||dut.wb_v))begin
      if(dut.id_advance)$fatal(1,"valid CSR bypassed serial wait");
      serial_holds++;
    end
    word=rst_n&&imem_valid ? instruction(imem_addr) : stale_word;
    redirect=rst_n&&dut.ex_redirect;
    clk=1;#2;imem_rdata=word;
    if(redirect)expect_target=1;
    if(rst_n&&trap_valid)$fatal(1,"unowned stale instruction trapped");
    if(rst_n&&commit_valid)begin
      if(commit_pc!==(commits<3 ? BASE+4*commits : BASE+4*(commits+1)))
        $fatal(1,"fetch token lost or wrong-path instruction retired");
      if(commit_insn!==instruction(commit_pc) || commit_mem_wstrb!==0)
        $fatal(1,"paired word/side effect mismatch");
      if(commits==3 && (commit_rd!==2 || commit_wdata!==2))$fatal(1,"target arithmetic mismatch");
      if(commits==4 && (commit_rd!==3 || commit_wdata!==0))$fatal(1,"valid CSR mismatch");
      commits++;
    end
    clk=0;#2;
  endtask
  initial begin
    for(integer m=0;m<3;m++)for(integer s=0;s<2;s++)begin
      mode=m;stale_word=s==0 ? 32'h340021f3 : 32'h30200073;
      commits=0;serial_holds=0;redirect_fetches=0;expect_target=0;
      rst_n=0;imem_rdata=32'h13;step();step();rst_n=1;
      for(integer n=0;n<100 && commits<5;n++)step();
      if(commits!=5 || redirect_fetches!=1 || serial_holds==0)$fatal(1,"stale fetch scenario incomplete");
      $display("STALE_FETCH_CASE enabled=%0d redirect=%0d stale=%h commits=%0d serial_holds=%0d",ENABLE,m,stale_word,commits,serial_holds);
      cases++;
    end
    $display("STALE_FETCH_PASS enabled=%0d cases=%0d",ENABLE,cases);$finish;
  end
  initial begin #100000;$fatal(1,"stale fetch timeout");end
endmodule
