`timescale 1ps/1ps
module __hullcirq_contract_tb;
// Saved independent vectors; no DUT-derived golden output.
reg hc_p0;
reg hc_p1;
reg [7:0] hc_p2;
reg hc_p3;
wire hc_p4;
reg [7:0] hc_p5;
reg hc_p6;
wire hc_p7;
reg [7:0] hc_p8;
reg hc_p9;
wire hc_p10;
reg [7:0] hc_p11;
reg hc_p12;
wire hc_p13;
wire [3:0] hc_p14;
wire hc_p15;
reg hc_p16;
wire [3:0] hc_p17;
wire hc_p18;
reg hc_p19;
wire [3:0] hc_p20;
wire hc_p21;
reg hc_p22;
wire [3:0] hc_p23;
wire hc_p24;
reg hc_p25;
release_saturating_array_top dut (.clk_array(hc_p0),.rst_array_n(hc_p1),.lane00_data_i(hc_p2),.lane00_data_i_valid(hc_p3),.lane00_data_i_ready(hc_p4),.lane01_data_i(hc_p5),.lane01_data_i_valid(hc_p6),.lane01_data_i_ready(hc_p7),.lane10_data_i(hc_p8),.lane10_data_i_valid(hc_p9),.lane10_data_i_ready(hc_p10),.lane11_data_i(hc_p11),.lane11_data_i_valid(hc_p12),.lane11_data_i_ready(hc_p13),.lane00_data_o(hc_p14),.lane00_data_o_valid(hc_p15),.lane00_data_o_ready(hc_p16),.lane01_data_o(hc_p17),.lane01_data_o_valid(hc_p18),.lane01_data_o_ready(hc_p19),.lane10_data_o(hc_p20),.lane10_data_o_valid(hc_p21),.lane10_data_o_ready(hc_p22),.lane11_data_o(hc_p23),.lane11_data_o_valid(hc_p24),.lane11_data_o_ready(hc_p25));
initial begin
hc_p0=0;
// Saved cycle 0
hc_p1=1'b0;
hc_p2=8'h0;
hc_p3=1'h0;
hc_p5=8'h0;
hc_p6=1'h0;
hc_p8=8'h0;
hc_p9=1'h0;
hc_p11=8'h0;
hc_p12=1'h0;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=0 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h0, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h0, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h0, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h0, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h0, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h0, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=0 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=0 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h0, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 1
hc_p1=1'b1;
hc_p2=8'h77;
hc_p3=1'h1;
hc_p5=8'h23;
hc_p6=1'h1;
hc_p8=8'h87;
hc_p9=1'h1;
hc_p11=8'h0;
hc_p12=1'h0;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=1 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h5, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane10_data_o expected=%h actual=%h", 4'hf, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h0, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=1 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=1 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h0, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 2
hc_p1=1'b1;
hc_p2=8'h88;
hc_p3=1'h1;
hc_p5=8'hf1;
hc_p6=1'h1;
hc_p8=8'h0;
hc_p9=1'h0;
hc_p11=8'h99;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=2 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h8, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane10_data_o expected=%h actual=%h", 4'hf, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h8, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=2 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=2 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 3
hc_p1=1'b1;
hc_p2=8'h23;
hc_p3=1'h1;
hc_p5=8'h0;
hc_p6=1'h0;
hc_p8=8'h46;
hc_p9=1'h1;
hc_p11=8'h70;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=3 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h5, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=3 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=3 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 4
hc_p1=1'b1;
hc_p2=8'h0;
hc_p3=1'h0;
hc_p5=8'h87;
hc_p6=1'h1;
hc_p8=8'h99;
hc_p9=1'h1;
hc_p11=8'h77;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=4 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h5, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h0, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h8, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=4 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=4 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 5
hc_p1=1'b1;
hc_p2=8'hf1;
hc_p3=1'h1;
hc_p5=8'h87;
hc_p6=1'h1;
hc_p8=8'h70;
hc_p9=1'h1;
hc_p11=8'h77;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=5 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h0, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane01_data_o expected=%h actual=%h", 4'hf, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=5 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=5 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 6
hc_p1=1'b1;
hc_p2=8'h87;
hc_p3=1'h1;
hc_p5=8'h46;
hc_p6=1'h1;
hc_p8=8'h0;
hc_p9=1'h0;
hc_p11=8'h77;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=6 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h0, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h7, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=6 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=6 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 7
hc_p1=1'b1;
hc_p2=8'h87;
hc_p3=1'h1;
hc_p5=8'h0;
hc_p6=1'h0;
hc_p8=8'h77;
hc_p9=1'h1;
hc_p11=8'h88;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=7 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane00_data_o expected=%h actual=%h", 4'hf, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h7, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h0, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h8, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=7 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=7 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 8
hc_p1=1'b1;
hc_p2=8'h0;
hc_p3=1'h0;
hc_p5=8'h99;
hc_p6=1'h1;
hc_p8=8'h77;
hc_p9=1'h1;
hc_p11=8'h23;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=8 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane00_data_o expected=%h actual=%h", 4'hf, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h0, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h8, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h5, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=8 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=8 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 9
hc_p1=1'b1;
hc_p2=8'h46;
hc_p3=1'h1;
hc_p5=8'h70;
hc_p6=1'h1;
hc_p8=8'h88;
hc_p9=1'h1;
hc_p11=8'h0;
hc_p12=1'h0;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=9 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h8, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h8, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h5, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=9 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=9 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 10
hc_p1=1'b1;
hc_p2=8'h99;
hc_p3=1'h1;
hc_p5=8'h70;
hc_p6=1'h1;
hc_p8=8'h0;
hc_p9=1'h0;
hc_p11=8'hf1;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=10 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h7, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h8, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h0, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h5, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=10 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=10 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 11
hc_p1=1'b1;
hc_p2=8'h99;
hc_p3=1'h1;
hc_p5=8'h0;
hc_p6=1'h0;
hc_p8=8'h23;
hc_p9=1'h1;
hc_p11=8'hf1;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=11 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h7, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h0, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h5, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h0, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=11 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=11 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 12
hc_p1=1'b0;
hc_p2=8'h99;
hc_p3=1'h0;
hc_p5=8'h0;
hc_p6=1'h0;
hc_p8=8'h0;
hc_p9=1'h0;
hc_p11=8'h0;
hc_p12=1'h0;
hc_p16=1'h1;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=12 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h0, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h0, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h0, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h0, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h0, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h0, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=12 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=12 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h0, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 13
hc_p1=1'b1;
hc_p2=8'h99;
hc_p3=1'h1;
hc_p5=8'h77;
hc_p6=1'h1;
hc_p8=8'hf1;
hc_p9=1'h1;
hc_p11=8'h0;
hc_p12=1'h0;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=13 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h8, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h7, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h0, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h0, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=13 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=13 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h0, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 14
hc_p1=1'b1;
hc_p2=8'h70;
hc_p3=1'h1;
hc_p5=8'h88;
hc_p6=1'h1;
hc_p8=8'h0;
hc_p9=1'h0;
hc_p11=8'h87;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=14 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h7, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h0, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h0, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane11_data_o expected=%h actual=%h", 4'hf, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=14 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=14 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 15
hc_p1=1'b1;
hc_p2=8'h77;
hc_p3=1'h1;
hc_p5=8'h88;
hc_p6=1'h1;
hc_p8=8'h87;
hc_p9=1'h1;
hc_p11=8'h46;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=15 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h8, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane10_data_o expected=%h actual=%h", 4'hf, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane11_data_o expected=%h actual=%h", 4'hf, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=15 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=15 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 16
hc_p1=1'b1;
hc_p2=8'h77;
hc_p3=1'h1;
hc_p5=8'h23;
hc_p6=1'h1;
hc_p8=8'h46;
hc_p9=1'h1;
hc_p11=8'h46;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=16 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h5, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane10_data_o expected=%h actual=%h", 4'hf, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=16 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=16 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 17
hc_p1=1'b1;
hc_p2=8'h77;
hc_p3=1'h1;
hc_p5=8'hf1;
hc_p6=1'h1;
hc_p8=8'h46;
hc_p9=1'h1;
hc_p11=8'h0;
hc_p12=1'h0;
hc_p16=1'h1;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=17 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h7, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane10_data_o expected=%h actual=%h", 4'hf, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=17 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=17 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h0, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 18
hc_p1=1'b1;
hc_p2=8'h88;
hc_p3=1'h1;
hc_p5=8'h87;
hc_p6=1'h1;
hc_p8=8'h46;
hc_p9=1'h1;
hc_p11=8'h99;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=18 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h8, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h8, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=18 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=18 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 19
hc_p1=1'b1;
hc_p2=8'h23;
hc_p3=1'h1;
hc_p5=8'h87;
hc_p6=1'h1;
hc_p8=8'h99;
hc_p9=1'h1;
hc_p11=8'h70;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=19 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h5, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h0, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h8, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h8, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=19 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=19 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 20
hc_p1=1'b1;
hc_p2=8'h0;
hc_p3=1'h0;
hc_p5=8'h87;
hc_p6=1'h1;
hc_p8=8'h70;
hc_p9=1'h1;
hc_p11=8'h70;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h1;
hc_p25=1'h0;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=20 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h0, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h5, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane01_data_o expected=%h actual=%h", 4'hf, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h8, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=20 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=20 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 21
hc_p1=1'b1;
hc_p2=8'hf1;
hc_p3=1'h1;
hc_p5=8'h46;
hc_p6=1'h1;
hc_p8=8'h77;
hc_p9=1'h1;
hc_p11=8'h70;
hc_p12=1'h1;
hc_p16=1'h0;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=21 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h0, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h5) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h5, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h7, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=21 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=21 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 22
hc_p1=1'b1;
hc_p2=8'hf1;
hc_p3=1'h1;
hc_p5=8'h99;
hc_p6=1'h1;
hc_p8=8'h77;
hc_p9=1'h1;
hc_p11=8'h77;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h1;
hc_p22=1'h0;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=22 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h1, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h0, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'h0) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane00_data_o expected=%h actual=%h", 4'h0, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h8, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h7, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=22 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=22 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
// Saved cycle 23
hc_p1=1'b1;
hc_p2=8'h87;
hc_p3=1'h1;
hc_p5=8'h0;
hc_p6=1'h0;
hc_p8=8'h77;
hc_p9=1'h1;
hc_p11=8'h88;
hc_p12=1'h1;
hc_p16=1'h1;
hc_p19=1'h0;
hc_p22=1'h1;
hc_p25=1'h1;
#25000; hc_p0=1; #1000;
$display("HULLCIRQ_CYCLE cycle=23 signal=lane00_data_i_ready value=%h", hc_p4);
if (hc_p4 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane00_data_i_ready expected=%h actual=%h", 1'h1, hc_p4); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane01_data_i_ready value=%h", hc_p7);
if (hc_p7 !== 1'h0) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane01_data_i_ready expected=%h actual=%h", 1'h0, hc_p7); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane10_data_i_ready value=%h", hc_p10);
if (hc_p10 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane10_data_i_ready expected=%h actual=%h", 1'h1, hc_p10); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane11_data_i_ready value=%h", hc_p13);
if (hc_p13 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane11_data_i_ready expected=%h actual=%h", 1'h1, hc_p13); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane00_data_o value=%h", hc_p14);
if (hc_p14 !== 4'hf) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane00_data_o expected=%h actual=%h", 4'hf, hc_p14); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane00_data_o_valid value=%h", hc_p15);
if (hc_p15 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane00_data_o_valid expected=%h actual=%h", 1'h1, hc_p15); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane01_data_o value=%h", hc_p17);
if (hc_p17 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane01_data_o expected=%h actual=%h", 4'h8, hc_p17); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane01_data_o_valid value=%h", hc_p18);
if (hc_p18 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane01_data_o_valid expected=%h actual=%h", 1'h1, hc_p18); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane10_data_o value=%h", hc_p20);
if (hc_p20 !== 4'h7) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane10_data_o expected=%h actual=%h", 4'h7, hc_p20); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane10_data_o_valid value=%h", hc_p21);
if (hc_p21 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane10_data_o_valid expected=%h actual=%h", 1'h1, hc_p21); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane11_data_o value=%h", hc_p23);
if (hc_p23 !== 4'h8) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane11_data_o expected=%h actual=%h", 4'h8, hc_p23); $finish; end
$display("HULLCIRQ_CYCLE cycle=23 signal=lane11_data_o_valid value=%h", hc_p24);
if (hc_p24 !== 1'h1) begin $display("HULLCIRQ_FAIL cycle=23 phase=after signal=lane11_data_o_valid expected=%h actual=%h", 1'h1, hc_p24); $finish; end
#24000; hc_p0=0;
$display("HULLCIRQ_PASS vectors=24 vector_hash=c8fad96714060849bf1e5c25ba0a0b22d9c37f866f6363ee0c0f24c934d87c0f");
$finish;
end
endmodule
