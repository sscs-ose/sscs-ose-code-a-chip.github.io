`timescale 1ps/1ps
module __hullcirq_contract_tb;
// Saved independent vectors; no DUT-derived golden output.
reg hc_p0;
reg hc_p1;
reg [3:0] hc_p2;
reg hc_p3;
wire hc_p4;
wire [3:0] hc_p5;
wire hc_p6;
reg hc_p7;
release_counter dut (.clk_ctr(hc_p0),.rst_ctr(hc_p1),.data_in(hc_p2),.data_in_valid(hc_p3),.data_in_ready(hc_p4),.data_out(hc_p5),.data_out_valid(hc_p6),.data_out_ready(hc_p7));
initial begin
hc_p0=0;
// Saved cycle 0
hc_p1=1'b1;
hc_p2=4'h0;
hc_p3=1'h0;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=0 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=data_out expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=data_out_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 1
hc_p1=1'b0;
hc_p2=4'h1;
hc_p3=1'h0;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=1 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=data_out expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=data_out_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 2
hc_p1=1'b0;
hc_p2=4'hf;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=2 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=data_out expected=%h actual=%h", 4'hf, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 3
hc_p1=1'b0;
hc_p2=4'h1;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=3 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=data_out expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 4
hc_p1=1'b0;
hc_p2=4'h7;
hc_p3=1'h1;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=4 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=data_in_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=data_out expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 5
hc_p1=1'b0;
hc_p2=4'h7;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=5 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=data_out expected=%h actual=%h", 4'h7, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 6
hc_p1=1'b0;
hc_p2=4'h3;
hc_p3=1'h0;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=6 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=data_in_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=data_out expected=%h actual=%h", 4'h7, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 7
hc_p1=1'b0;
hc_p2=4'h3;
hc_p3=1'h0;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=7 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=data_out expected=%h actual=%h", 4'h7, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=data_out_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 8
hc_p1=1'b0;
hc_p2=4'h4;
hc_p3=1'h1;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=8 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=data_in_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'hb) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=data_out expected=%h actual=%h", 4'hb, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 9
hc_p1=1'b1;
hc_p2=4'h9;
hc_p3=1'h1;
hc_p7=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=9 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=data_out expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=data_out_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 10
hc_p1=1'b0;
hc_p2=4'h2;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=10 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h2) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=data_out expected=%h actual=%h", 4'h2, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 11
hc_p1=1'b0;
hc_p2=4'h0;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=11 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h2) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=data_out expected=%h actual=%h", 4'h2, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 12
hc_p1=1'b0;
hc_p2=4'h1;
hc_p3=1'h0;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=12 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h2) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=data_out expected=%h actual=%h", 4'h2, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=data_out_valid expected=%h actual=%h", 1'h0, hc_p6); $finish; end
#24000; hc_p0=0;
// Saved cycle 13
hc_p1=1'b0;
hc_p2=4'he;
hc_p3=1'h1;
hc_p7=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=13 signal=data_in_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=data_in_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=data_out value=%h", hc_p5);
if (hc_p5 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=data_out expected=%h actual=%h", 4'h0, hc_p5); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=data_out_valid value=%h", hc_p6);
if (hc_p6 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=data_out_valid expected=%h actual=%h", 1'h1, hc_p6); $finish; end
#24000; hc_p0=0;
$display("HULLCIRQ_PASS vectors=14 vector_hash=09d192cf4a9b02fed86c21667fe6b6371556273966c8b355ed0fa4a75c082932");
$finish;
end
  initial begin
    $display("HULLCIRQ_ZERO_DELAY_WAVEFORM");
    $dumpfile("simulation.vcd");
    $dumpvars(1, __hullcirq_contract_tb);
  end
endmodule
