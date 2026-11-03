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


/* 
   ADC Oversampler of [1,4,16,64,256] samples where 4**N samples equal +N Bit resolution
   Input vector has 12 Bit, result has 16 Bit 
   data_in =  [ 12 Bit input  ] Range 12'h000  = -VCC ... 12'hFFF  = +VCC
   data_out = [ 16 Bit result ] Range 16'h0000 = -VCC ... 16'hFFF0 = +VCC
*/

module adc_osr (
   input wire rst_n,
   input wire data_valid_strobe,
   input wire [2:0] osr_mode_in,
   input wire [11:0] data_in,
   output wire [15:0] data_out,
   output wire conversion_finished_osr_out
   );

   // internal registers
   reg  [19:0] result_r;
   reg  [2:0]  osr_mode_r;
   reg  [8:0]  sample_count_r;
   reg  [15:0] output_r;
   reg         data_valid_r;

   // combinatoric signals for next register values
   wire [19:0] next_result_w;
   wire [2:0]  next_osr_mode_w;
   wire [8:0]  next_sample_count_w;
   wire [15:0] next_output_w;

   // Direct signals
   assign conversion_finished_osr_out = data_valid_r & data_valid_strobe;
   
   //******************************************
   //   data_valid_strobe as clock input
   //******************************************
   // Cave: Handle with care, normally you should 
   // only use one clk-signal to guarantee synchronous 
   // execution without problems

   always @(posedge data_valid_strobe, negedge rst_n) begin
      if (rst_n == 1'b0) begin  
         result_r          <= 20'd0;
         osr_mode_r        <=  3'd0;
         sample_count_r    <=  9'd1;
         output_r          <=  16'd0;
         data_valid_r      <=  1'b0;
      end 
      else begin	
         result_r        <= next_result_w;
         osr_mode_r      <= next_osr_mode_w;
         sample_count_r  <= next_sample_count_w;
         output_r        <= next_output_w;
         data_valid_r    <= next_data_valid_w;
      end
   end 

   wire next_data_valid_w = is_last_sample;
  

   //*******************************
   //   State flags
   //*******************************
   wire bypass_oversampling = ~(osr_mode_in[0] | osr_mode_in[1] | osr_mode_in==3'b100);
   wire is_first_sample = bypass_oversampling | (sample_count_r == 9'd1);
   wire is_last_sample  = bypass_oversampling | ((sample_count_r == osr_count_limit_w)&&(~is_first_sample));

   //*******************************
   //   Combinatoric signals
   //*******************************
   assign next_result_w        = is_first_sample ? {8'd0,data_in} : 
                                                   {8'd0,data_in} + result_r;

   assign next_osr_mode_w      = is_first_sample ? osr_mode_in : osr_mode_r;
   assign next_sample_count_w  = is_last_sample ? 1 : sample_count_r + 1;

    //***********************************************
    //   Output right-shifted result
    //***********************************************
    assign data_out = output_r;
    
    assign next_output_w = bypass_oversampling    ? {next_result_w[11:0],4'b0} :
                           ~is_last_sample        ? output_r                   :
                           (osr_mode_r == 3'b001) ? {next_result_w[13:1],3'b0} :
                           (osr_mode_r == 3'b010) ? {next_result_w[15:2],2'b0} :
                           (osr_mode_r == 3'b011) ? {next_result_w[17:3],1'b0} :
                           (osr_mode_r == 3'b100) ? {next_result_w[19:4]}      :
                           16'bX; 
                      
    //***********************************************
    //   OSR mode lookup table
    //   mode 001 = 4 samples   +1 Bit resolution
    //   mode 010 = 16 samples  +2 Bit resolution
    //   mode 011 = 64 samples  +3 Bit resolution
    //   mode 100 = 256 samples +4 Bit resolution
    //***********************************************
    // Amount of oversampling samples (+N Bit SNR per N*4 samples)
    wire [8:0] osr_count_limit_w = (osr_mode_r == 3'b001) ? 9'd4   :
                                   (osr_mode_r == 3'b010) ? 9'd16  :
                                   (osr_mode_r == 3'b011) ? 9'd64  :
                                   (osr_mode_r == 3'b100) ? 9'd256 :
                                   9'd1;
endmodule





