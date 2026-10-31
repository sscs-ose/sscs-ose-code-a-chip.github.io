
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
`default_nettype none


// Top module ADC Control
module adc_control_nonbinary #(parameter MATRIX_BITS = 12, NONBINARY_REDUNDANCY = 3)(
   input wire clk,
   input wire rst_n,
   input wire comparator_in,
   input wire [2:0] avg_control_in,
   output wire sample_out,
   output wire sample_out_n,
   output wire enable_loop_out,
   output wire conv_finished_strobe_out,
   output wire[MATRIX_BITS-1:0]  pswitch_out,
   output wire[MATRIX_BITS-1:0]  nswitch_out,
   output reg[MATRIX_BITS-1:0]   result_out
   );

   // combinatoric signals for next register values
   wire [MATRIX_BITS-1:0] next_result_w;
   wire [4:0] next_average_counter_w;
   wire [4:0] next_average_sum_w;
   wire [2:0] next_sampled_avg_control_w;
   wire [MATRIX_BITS+NONBINARY_REDUNDANCY+1:0] next_shift_register_w;
   wire [MATRIX_BITS-1:0] next_data_register_w;
   
   // Average calculation of comparator_in at LSB-region
   reg [4:0] average_counter_r;
   reg [4:0] average_sum_r;
   reg [2:0] sampled_avg_control_r;
   wire [4:0] average_count_limit_w;
   wire averaged_comparator_in_w;
   wire lsb_region_w        = (shift_register_r[2] | shift_register_r[3] | shift_register_r[4] | shift_register_r[5]);
   wire is_averaging_w      = (lsb_region_w && (average_counter_r < average_count_limit_w));
   
   // State-Machine Shift Register
   reg [MATRIX_BITS+NONBINARY_REDUNDANCY+1:0] shift_register_r;
   reg [MATRIX_BITS-1:0] data_register_r;
   wire [MATRIX_BITS-1:0] nonbinary_value_w;

  // State machine states
   wire is_holding_result_w = shift_register_r[1];
   wire is_sampling_w       = shift_register_r[0];
   wire result_ready_w = ((shift_register_r[2]==1'b1)&~is_averaging_w);
   wire result_strobe_w = ((shift_register_r[1]==1'b1)&~is_averaging_w);


  /* 
  *************************************************
  //wire hold_data_for_osr   = shift_register_r[1];
  *************************************************

    OSR uses the data-valid strobe as clock-signal for low power, 
    which can lead to unpredictable problems. 
    
    expected:
    data_in         XXXXX__data___XXXX
    data_valid      _____/‾‾‾‾‾‾\_____
    data_valid_clk  ____________/‾‾\__

    Possible problem:
    data_in         XXXXX__data___XXXXXX
    data_valid      _____/‾‾‾‾‾‾\_______
    data_valid_clk  ______________/‾‾\__ Clock is delayed

    Solution: Data at OSR input is held for two clock cycles
    data_in         XXXXX__data_________XXXXXX
    data_valid      _____/‾‾‾‾‾‾\_______
    data_valid_clk  ______________/‾‾\__ Clock can have delay

  */
   

   // conversion finished set 0 after reset, 1 after conversion ended
   wire next_conv_finished_w = result_strobe_w;
   reg  conv_finished_r;


   //******************************************
   //   Synchronous process and Reset Handling
   //******************************************
   always @(posedge clk, negedge rst_n) begin
      if (rst_n == 1'b0) begin  
         result_out            <= {MATRIX_BITS{1'b0}};
         shift_register_r      <= {{(MATRIX_BITS+NONBINARY_REDUNDANCY+1){1'b0}},1'b1};     
         sampled_avg_control_r <= 3'b000;   
         average_counter_r     <= 5'd1;
         average_sum_r         <= 5'd0;
         data_register_r       <= 12'd2048; 
         conv_finished_r       <= 1'b0;
      end 
      else begin	
         result_out            <= next_result_w;
         shift_register_r      <= next_shift_register_w; 
         sampled_avg_control_r <= next_sampled_avg_control_w; 
         average_counter_r     <= next_average_counter_w;
         average_sum_r         <= next_average_sum_w;
         data_register_r       <= next_data_register_w;
         conv_finished_r       <= next_conv_finished_w;
      end
   end 

   //*******************************
   //   Combinatorial Processes
   //*******************************

   // direct output values determined from internal registers
   assign sample_out        = is_sampling_w;
   assign sample_out_n       = ~is_sampling_w;
   assign conv_finished_strobe_out = conv_finished_r;
   assign enable_loop_out        = ~is_sampling_w;
   assign pswitch_out      = ~data_register_r;
   assign nswitch_out      = data_register_r;

   // shift register and data handling
   // save avg_control in a register to prevent changes of this value during conversion
   assign next_shift_register_w      = is_averaging_w ? shift_register_r : {shift_register_r[0],shift_register_r[MATRIX_BITS+NONBINARY_REDUNDANCY+1:1]};
   assign next_sampled_avg_control_w = is_sampling_w ? avg_control_in : sampled_avg_control_r;
   
   wire [MATRIX_BITS-1:0] sar_up   = data_register_r+nonbinary_value_w;
   wire [MATRIX_BITS-1:0] sar_down = data_register_r-nonbinary_value_w;
   assign next_data_register_w = is_sampling_w | is_holding_result_w | result_ready_w ? 12'd2048 :
                                 is_averaging_w ? data_register_r :
                                 averaged_comparator_in_w ? sar_up : sar_down ;
   
   // update the result at end of conversion
   //assign next_result_w = result_ready_w ? next_data_register_w : result_out;
   assign next_result_w = (result_ready_w &  averaged_comparator_in_w) ? data_register_r   : 
                          (result_ready_w & ~averaged_comparator_in_w) ? data_register_r-1 :
                          result_out;
   
   // Get the comparator_in average value.
   // Sum up comparator_in while in LSB region.
   // Afterwards the result in average_sum is evaluated.
   assign next_average_counter_w   = is_averaging_w ? average_counter_r+1 : 5'd1;
   assign next_average_sum_w       = is_averaging_w ? average_sum_r+{4'b0,comparator_in} : {4'b0, comparator_in};
   assign averaged_comparator_in_w = (~lsb_region_w) ? comparator_in :
                                     is_averaging_w ? 1'b0 :
                                     (average_count_limit_w ==  5'd3) ? average_sum_r[1] :
                                     (average_count_limit_w ==  5'd7) ? average_sum_r[2] :
                                     (average_count_limit_w ==  5'd15) ? average_sum_r[3] :
                                     (average_count_limit_w ==  5'd31) ? average_sum_r[4] :
                                     comparator_in;



   //*******************************
   //   NONBINARY Lookup table
   //*******************************
   // calculated for 12 Bit Matrix + 3 redundant Bits
    assign nonbinary_value_w = (shift_register_r==17'd2**16) ? 12'd806 :
                               (shift_register_r==17'd2**15) ? 12'd486 :
                               (shift_register_r==17'd2**14) ? 12'd295 :
                               (shift_register_r==17'd2**13) ? 12'd180 :
                               (shift_register_r==17'd2**12) ? 12'd110 :
                               (shift_register_r==17'd2**11) ? 12'd67 :
                               (shift_register_r==17'd2**10) ? 12'd41 :
                               (shift_register_r==17'd2**9 ) ? 12'd25 :
                               (shift_register_r==17'd2**8 ) ? 12'd15 :
                               (shift_register_r==17'd2**7 ) ? 12'd9 :
                               (shift_register_r==17'd2**6 ) ? 12'd6 :
                               (shift_register_r==17'd2**5 ) ? 12'd4 :
                               (shift_register_r==17'd2**4 ) ? 12'd2 :
                               (shift_register_r==17'd2**3 ) ? 12'd1 :
                               (shift_register_r==17'd2**2 ) ? 12'd0 :
                               (shift_register_r==17'd2**1 ) ? 12'd0 :
                               (shift_register_r==17'd2**0 ) ? 12'd0 :
                               12'dX; // default signal for illegal state

    //*******************************
    //   AVERAGING lookup table
    //*******************************
    // Amount of measurements to average comparator_in at LSB_region
    assign average_count_limit_w = (sampled_avg_control_r == 3'b001) ? 5'd3  :
                                   (sampled_avg_control_r == 3'b010) ? 5'd7  :
                                   (sampled_avg_control_r == 3'b011) ? 5'd15 :
                                   (sampled_avg_control_r == 3'b100) ? 5'd31 :
                                   5'd1;
    
endmodule





