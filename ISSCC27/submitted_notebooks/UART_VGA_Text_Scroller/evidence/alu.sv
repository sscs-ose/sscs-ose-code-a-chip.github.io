
`timescale 1ns/1ps
module tb_alu;
  reg clk=0, rst_n=0, ena=1;
  // Start with a nonzero vector: the first test vector is zero.
  // This guarantees an input transition to trigger always @* in Icarus.
  reg [7:0] ui_in=8'h08, uio_in=8'h3F;
  wire [7:0] uo_out,uio_out,uio_oe;
  integer a,b,sel,expect_y,got_y,count=0;
  tt_um_nobleg30_uart_vga_scroller dut(
    .ui_in(ui_in),.uo_out(uo_out),.uio_in(uio_in),.uio_out(uio_out),.uio_oe(uio_oe),
    .ena(ena),.clk(clk),.rst_n(rst_n));
  initial begin
    #5;
    if (uio_oe !== 8'hC0) $fatal(1,"Wrong uio_oe");
    for(sel=0;sel<4;sel=sel+1)
      for(b=0;b<4;b=b+1)
        for(a=0;a<4;a=a+1) begin
          uio_in=a|(b<<2)|(sel<<4);
          #5;
          case(sel)
           0: expect_y=(a+b)&3;
           1: expect_y=(a-b)&3;
           2: expect_y=a&b;
           default:expect_y=a^b;
          endcase
          got_y=(uio_out>>6)&3;
          if (got_y !== expect_y || uio_out[5:0] !== 6'b000000)
            $fatal(1,"Mismatch A=%0d B=%0d SEL=%0d got=%0d expected=%0d",a,b,sel,got_y,expect_y);
          count=count+1;
        end
    $display("RTL_PASS: ALU checked %0d/64 patterns; output-enable 0x%02h",count,uio_oe);
    $finish;
  end
endmodule
