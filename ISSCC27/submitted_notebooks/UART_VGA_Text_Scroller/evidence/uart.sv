
`timescale 1ns/1ps
module tb_uart;
  reg clk=0,rst_n=0,ena=1;
  reg [7:0] ui_in=8'h08,uio_in=0;
  wire [7:0] uo_out,uio_out,uio_oe;
  tt_um_nobleg30_uart_vga_scroller dut(
    .ui_in(ui_in),.uo_out(uo_out),.uio_in(uio_in),.uio_out(uio_out),.uio_oe(uio_oe),
    .ena(ena),.clk(clk),.rst_n(rst_n));
  always #5 clk=~clk;
  task send_byte(input [7:0] value);
    integer k;
    begin
       ui_in[3]=0;repeat(2622) @(negedge clk);
       for(k=0;k<8;k=k+1) begin
         ui_in[3]=value[k]; repeat(2622) @(negedge clk);
       end
       ui_in[3]=1;repeat(2622) @(negedge clk);
       repeat(8) @(negedge clk);
    end
  endtask
  initial begin
    repeat(8) @(negedge clk);
    rst_n=1;
    send_byte(8'h41);  // 'A' -> 1
    send_byte(8'h62);  // 'b' -> 2
    send_byte(8'h3F);  // '?' -> 40
    if(dut.msg_len !== 3 || dut.write_ptr !== 3 ||
       dut.msg_mem[0] !== 1 || dut.msg_mem[1] !== 2 || dut.msg_mem[2] !== 40)
       $fatal(1,"UART buffer: len=%0d ptr=%0d mem=%0d,%0d,%0d",dut.msg_len,dut.write_ptr,dut.msg_mem[0],dut.msg_mem[1],dut.msg_mem[2]);
    send_byte(8'h0D); // Carriage return
    if(dut.msg_len !== 3 || dut.write_ptr !== 0 || dut.scroll_pos !== 0)
      $fatal(1,"CR semantics wrong: len=%0d ptr=%0d scroll=%0d",dut.msg_len,dut.write_ptr,dut.scroll_pos);
    $display("RTL_PASS: UART bytes A,b,? stored 1,2,40; CR restarts pointer without clearing msg_len");
    $finish;
  end
endmodule
