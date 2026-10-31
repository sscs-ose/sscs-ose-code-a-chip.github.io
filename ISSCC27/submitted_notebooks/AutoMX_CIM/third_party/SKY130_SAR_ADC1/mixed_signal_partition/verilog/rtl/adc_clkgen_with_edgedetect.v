`default_nettype none
//  Copyright 2022 Manuel Moser
//
//   Licensed under the Apache License, Version 2.0 (the "License");
//   you may not use this file except in compliance with the License.
//   You may obtain a copy of the License at
//
//       http://www.apache.org/licenses/LICENSE-2.0
//
//   Unless required by applicable law or agreed to in writing, software
//   distributed under the License is distributed on an "AS IS" BASIS,
//   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//   See the License for the specific language governing permissions and
//   limitations under the License.


// Asynchronous Clockgenerator with Edge-Detection for self-clocked ADC.
//
// Important: This verilog-file can not be synthesized with openlane-Optimizations 
//            activated. Delays will be subsitituted otherwise. Verify in xschem with postlayout extraction 
//            Harden with https://github.com/w32agobot/SKY130-RTL-with-Custom-Standardcell-to-GDSII

module adc_clkgen_with_edgedetect(
    input wire ena_in,             // enable signal from the digital clock core. 0 halts the self-clocked loop
    input wire start_conv_in,         // triggers a conversion once with edge-detection
    input wire ndecision_finish_in,   // comparator signalizes finished conversion
    output wire clk_dig_out,           // digital clock
    output wire clk_comp_out,          // comparator clock
    input wire enable_dlycontrol_in,  // 0 = max delays, 1 = configurable delays
    input wire [4:0] dlycontrol1_in,  // delay 1 of 3 in loop. Delay = 5ns*dlycontrol1
    input wire [4:0] dlycontrol2_in,  // delay 2 of 3 in loop. Delay = 5ns*dlycontrol2
    input wire [4:0] dlycontrol3_in,  // delay 3 of 3 in loop. Delay = 5ns*dlycontrol3
    input wire [5:0] dlycontrol4_in,  // edge detect pulse width. Delay = 5ns*dlycontrol4
    // integration of additional buffers for sample matrix
    input wire sample_p_in,           
    input wire sample_n_in,
    output wire sample_p_out,
    output wire sample_n_out
);
   wire enable_loop_w;
   wire ena_in_buffered_w;
   wire start_conv_buffered_w;
   wire ndecision_finish_buffered_w;
   wire clk_dig_unbuffered_w;
   wire clk_comp_unbuffered_w;

   //Input buffers
   sky130_fd_sc_hd__buf_1 inbuf_1 (.A(ena_in),.X(ena_in_buffered_w));
   sky130_fd_sc_hd__buf_1 inbuf_2 (.A(start_conv_in),.X(start_conv_buffered_w));
   sky130_fd_sc_hd__buf_1 inbuf_3 (.A(ndecision_finish_in),.X(ndecision_finish_buffered_w));
   
   //Output buffers
   sky130_fd_sc_hd__bufbuf_8 outbuf_1 (.A(clk_dig_unbuffered_w),.X(clk_dig_out));
   sky130_fd_sc_hd__bufbuf_8 outbuf_2 (.A(clk_comp_unbuffered_w),.X(clk_comp_out));

   // Output buffers for sample-signal-buffeing 
   // with delay, so matrix-sample is switched after gate is disabled
   wire sample_p_1;
   wire sample_n_1;

   //sample enable delay stage
   sky130_mm_sc_hd_dlyPoly5ns delay_sample_p11 (.in(sample_p_in), .out(sample_p_1));
   sky130_mm_sc_hd_dlyPoly5ns delay_sample_n12 (.in(sample_n_in), .out(sample_n_1));
   
   //sample enable output stage
   sky130_fd_sc_hd__bufbuf_8 outbuf_3 (.A(sample_p_1),.X(sample_p_out));
   sky130_fd_sc_hd__bufbuf_8 outbuf_4 (.A(sample_n_1),.X(sample_n_out));

   

   //Circuits
   adc_edge_detect_circuit edgedetect (.start_conv_in(start_conv_buffered_w),
                                       .ena_in(ena_in_buffered_w),
                                       .ena_out(enable_loop_w),
                                       .enable_dlycontrol_in(enable_dlycontrol_in),
                                       .dlycontrol_in(dlycontrol4_in));

   adc_clk_generation clkgen (.ndecision_finish_in(ndecision_finish_buffered_w),
                              .enable_loop_in(enable_loop_w),
                              .clk_dig_out(clk_dig_unbuffered_w),
                              .clk_comp_out(clk_comp_unbuffered_w),
                              .enable_dlycontrol_in(enable_dlycontrol_in),
                              .dlycontrol1_in(dlycontrol1_in),
                              .dlycontrol2_in(dlycontrol2_in),
                              .dlycontrol3_in(dlycontrol3_in));
endmodule

// generate the clock signals for comparator and digital core of the self-clocked SKY130_12Bit-SAR-ADC.
module adc_clk_generation(
   input wire ndecision_finish_in,   // 0 = comparator finished
   input wire enable_loop_in,        // 1 = self clocked loop enabled
   output wire clk_dig_out,           // clk for digital core
   output wire clk_comp_out,          // clk for comparator
   input wire enable_dlycontrol_in,  // 0 = max delays, 1 = configured delays
   input wire [4:0] dlycontrol1_in,  // delay1 = N times 5ns
   input wire [4:0] dlycontrol2_in,  // delay2 = N times 5ns
   input wire [4:0] dlycontrol3_in   // delay3 = N times 5ns
);
   wire ndecision_finish_delayed_w;
   wire clk_dig_delayed_w;
   wire net1_w;

    binary_delaycell #(.DLYCONTROL_BITWIDTH(5)) delay_155ns_1
    (
        .in(ndecision_finish_in), 
        .enable_dlycontrol_in(enable_dlycontrol_in), 
        .dlycontrol_in(dlycontrol1_in), 
        .out(ndecision_finish_delayed_w)
    );
    sky130_fd_sc_hd__inv_2 clkdig_inverter (.A(ndecision_finish_delayed_w),.Y(clk_dig_out));
    binary_delaycell #(.DLYCONTROL_BITWIDTH(5)) delay_155ns_2
    (
        .in(clk_dig_out), 
        .enable_dlycontrol_in(enable_dlycontrol_in), 
        .dlycontrol_in(dlycontrol2_in), 
        .out(clk_dig_delayed_w)
    );
    sky130_fd_sc_hd__nor2b_1 nor1 (.A(clk_dig_delayed_w),.B_N(enable_loop_in),.Y(net1_w)); //2 input nor, B inverted
    binary_delaycell #(.DLYCONTROL_BITWIDTH(5)) delay_155ns_3
    (
        .in(net1_w), 
        .enable_dlycontrol_in(enable_dlycontrol_in), 
        .dlycontrol_in(dlycontrol3_in), 
        .out(clk_comp_out)
    );
endmodule

// if ena_in is HIGH, then ena_out is HIGH.
// Else, detect the positive edge of start_conv and generate a pulsed signal at ena_out (low->high->low)
module adc_edge_detect_circuit(
    input wire start_conv_in,          // Tell the ADC to start a conversion
    input wire ena_in,              // signal from the digital core to enable the self-clocked-loop
    output wire ena_out,            // enable the self-clocked-loop
    input wire enable_dlycontrol_in,   // 0 = max delays, 1 = configured delays
    input wire [5:0] dlycontrol_in     // delay = N times 5ns
);   
   // Internal wires
    wire start_conv_delayed_w;
    wire start_conv_edge_w;
   
    binary_delaycell #(.DLYCONTROL_BITWIDTH(6)) dly_315ns_1
    (
        .in(start_conv_in), 
        .enable_dlycontrol_in(enable_dlycontrol_in), 
        .dlycontrol_in(dlycontrol_in), 
        .out(start_conv_delayed_w)
    );
    sky130_fd_sc_hd__nor2b_1 nor1 (.A(start_conv_delayed_w),.B_N(start_conv_in),.Y(start_conv_edge_w)); // 2 input nor, B inverted 
    sky130_fd_sc_hd__or2_1 or1 (.A(start_conv_edge_w),.B(ena_in),.X(ena_out)); // 2 input or
endmodule


// ####################################################
// delay cell with bypass control and enable-pin
// Delays eare binary coded. control_bitwidth sets the number
// of delay cells. Number of cells is 2^(control_bitwidth)-1
// Maximum delay is 5ns*(2^control_bitwidth-1)
module binary_delaycell #(parameter DLYCONTROL_BITWIDTH = 5)
(
    input wire in,
    input wire enable_dlycontrol_in,
    input wire [DLYCONTROL_BITWIDTH-1:0] dlycontrol_in,
    output wire out
);

    wire [DLYCONTROL_BITWIDTH:0] signal_w;
    wire enable_dlycontrol_w;
    wire [DLYCONTROL_BITWIDTH-1:0] bypass_enable_w;
    wire [DLYCONTROL_BITWIDTH-1:0] bypass_w;

    sky130_fd_sc_hd__buf_4 enablebuffer (.A(enable_dlycontrol_in),.X(enable_dlycontrol_w));
    
    //instanciate binary coded delay cells
    genvar i;
    generate
       for (i = 0; i < DLYCONTROL_BITWIDTH; i=i+1) begin
            sky130_fd_sc_hd__inv_2  control_invert (.A(dlycontrol_in[i]),.Y(bypass_enable_w[i]));
            sky130_fd_sc_hd__and2_1 bypass_enable (.A(enable_dlycontrol_w),.B(bypass_enable_w[i]),.X(bypass_w[i])); // 2 input and, A inverted
            delaycell #(.N_TIMES_5NS(2**i)) dly_binary (
                .in(signal_w[i]),
                .bypass_in(bypass_w[i]),
                .out(signal_w[i+1])
            );
        end
    endgenerate
    assign signal_w[0] = in;
    assign out = signal_w[DLYCONTROL_BITWIDTH];
endmodule


    // delaycell with bypass function
    //                                ___________                 bypass 
    //              _____            |   Ntimes  |                |-------\
    // bypass-----o| AND |--siga[0]--| Delay 5ns |------siga[N]---|0 mux   |--out--
    //       in-.--|_____|           |___________|   .--in--------|1______/
    //           \__________________________________/
    //
module delaycell #(parameter N_TIMES_5NS = 32)
(
    input wire in,
    input wire bypass_in,
    output wire out
);
    wire [N_TIMES_5NS:0] signal_w;          
    genvar j;
    generate
       for(j=0;j<N_TIMES_5NS;j=j+1) begin
          sky130_mm_sc_hd_dlyPoly5ns delay_unit (.in(signal_w[j]), .out(signal_w[j+1]));
       end             
    endgenerate
    sky130_fd_sc_hd__and2b_1 and_bypass_switch (.A_N(bypass_in),.B(in),.X(signal_w[0])); // 2 input and, A inverted
    sky130_fd_sc_hd__mux2_1 out_mux (.A0(signal_w[N_TIMES_5NS]),.A1(in),.S(bypass_in),.X(out)); //2 input mux
endmodule
