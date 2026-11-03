`timescale 1ps/1ps
module __hullcirq_contract_tb;
// Saved independent vectors; no DUT-derived golden output.
reg hc_p0;
reg hc_p1;
reg [7:0] hc_p2;
reg hc_p3;
wire hc_p4;
wire [3:0] hc_p5;
wire hc_p6;
reg hc_p7;
release_saturating_lane dut (.clk_array(hc_p0),.rst_array_n(hc_p1),.data_i(hc_p2),.data_i_valid(hc_p3),.data_i_ready(hc_p4),.data_o(hc_p5),.data_o_valid(hc_p6),.data_o_ready(hc_p7));
initial begin
hc_p0=0;
// Saved cycle 0
hc_p1=1'b0;
hc_p2=8'h0;
hc_p3=1'h0;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=0 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=data_o expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=data_o_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 1
hc_p1=1'b1;
hc_p2=8'h23;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=1 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=data_o expected=%h actual=%h", 4'h5, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 2
hc_p1=1'b1;
hc_p2=8'h77;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=2 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=data_o expected=%h actual=%h", 4'h7, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 3
hc_p1=1'b1;
hc_p2=8'h88;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=3 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=data_o expected=%h actual=%h", 4'h8, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 4
hc_p1=1'b1;
hc_p2=8'hf1;
hc_p3=1'h1;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=4 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=data_o expected=%h actual=%h", 4'h8, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 5
hc_p1=1'b1;
hc_p2=8'hf1;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=5 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=data_o expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 6
hc_p1=1'b1;
hc_p2=8'h87;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=6 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=data_o expected=%h actual=%h", 4'hf, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 7
hc_p1=1'b1;
hc_p2=8'h78;
hc_p3=1'h1;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=7 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=data_o expected=%h actual=%h", 4'hf, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 8
hc_p1=1'b1;
hc_p2=8'h78;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=8 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=data_o expected=%h actual=%h", 4'hf, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 9
hc_p1=1'b1;
hc_p2=8'h0;
hc_p3=1'h0;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=9 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=data_o expected=%h actual=%h", 4'hf, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=data_o_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 10
hc_p1=1'b1;
hc_p2=8'hff;
hc_p3=1'h1;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=10 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'he) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=data_o expected=%h actual=%h", 4'he, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 11
hc_p1=1'b0;
hc_p2=8'h0;
hc_p3=1'h0;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=11 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=data_o expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=data_o_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 12
hc_p1=1'b1;
hc_p2=8'hf8;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=12 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=data_o expected=%h actual=%h", 4'h8, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 13
hc_p1=1'b1;
hc_p2=8'h70;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=13 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=data_o expected=%h actual=%h", 4'h7, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 14
hc_p1=1'b1;
hc_p2=8'h99;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=14 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=data_o expected=%h actual=%h", 4'h8, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 15
hc_p1=1'b1;
hc_p2=8'h46;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=15 signal=data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=data_o value=%h", hc_p5);
if (hc_p5 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=data_o expected=%h actual=%h", 4'h7, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=data_o_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=data_o_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
$display("HULLCIRQ_PASS vectors=16 vector_hash=17462cb41c36095f86472b915d66a08067b26a202f46c3fb5e9d7a9dc340f9e9");
$finish;
end
  initial begin
    $display("HULLCIRQ_ZERO_DELAY_WAVEFORM");
    $dumpfile("simulation.vcd");
    $dumpvars(1, __hullcirq_contract_tb);
  end
endmodule
