/*
  Copyright 2022 Manuel Moser

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
`default_nettype none

/* 
   Convert Binary to (inverted) Thermo-Code for a
   capacitor-matrix with 16 rows, 32 columns and 3 Binary-Cells.

   row_mode=0 .. start with row 1 and progress up.. up.. up..
   row_mode=1 .. start at the middle row and progress up.. down.. up.. down..

   col_mode=0 .. start with col 1 (even) or col 32 (odd)
   col_mode=1 .. start at the middle column
*/

module adc_row_col_decoder(
    input  wire[11:0] data_in,
    input  wire row_mode,
    input  wire col_mode,
    output wire[15:0] row_out_n,
    output wire[15:0] rowon_out_n,
    output wire[15:0] rowoff_out_n,
    output wire[31:0] col_out_n,
    output wire[31:0] col_out,
    output wire[2:0]  bincap_out_n,
    output wire       c0p_out_n,
    output wire       c0n_out_n
	);

    
genvar i;

//[                data                ]
//[11][10][9][8][7][6][5][4][3][2][1][0]
//[    row     ][    col      ][bincap ]
wire[2:0] bincap_w = data_in[2:0];
wire[4:0] col_intermediate_w = data_in[7:3];
wire[3:0] row_intermediate_w = data_in[11:8];

wire row_direction_RL = row_intermediate_w[0] ; // romode  = 0 .. even/odd row is left to right
                                                           // rowmode = 1 .. lower half rows are left to right

// *********************************************
//   Row Decoder
//
//   Row Mode 0: from bot to top MSB[8 7 6 5 4 3 2 1]LSB
//   Row Mode 1: start at middle MSB[7 5 3 1 2 4 6 8]LSB
// *********************************************

/// Row Down-to-Up mode
wire[15:0] row_bottotop_n = ~(16'h0001<<row_intermediate_w);
wire[15:0] rowon_bottotop_n = (16'hFFFF<<row_intermediate_w);

/// Row Mid-to-Top/Bot mode
wire [15:0] row_midtoside_n;
wire [15:0] rowon_midtoside_n;
generate
  for (i=0;i<8;i=i+1) begin
    assign row_midtoside_n[8+i] = row_bottotop_n[2*i];
    assign row_midtoside_n[7-i] = row_bottotop_n[2*i+1];
    assign rowon_midtoside_n[8+i] = rowon_bottotop_n[2*i];
    assign rowon_midtoside_n[7-i] = rowon_bottotop_n[2*i+1];
  end
endgenerate

/// Row Out
assign row_out_n = row_mode ? row_midtoside_n : row_bottotop_n ;
assign rowon_out_n = row_mode ? rowon_midtoside_n : rowon_bottotop_n ;



// status
wire is_first_row = ~row_out_n[0];


// *********************************************
//   Column Decoder
//
//   Col Mode 0: Direction from side to side
//      even row: direction is left-to-right MSB[8 7 6 5 4 3 2 1]LSB
//		odd row:  direction is right-to-left MSB[7 5 3 1 2 4 6 8]LSB
//   Col Mode 1: Direction from middle to side MSB[8 6 4 2 1 3 5 7]LSB
// *********************************************

// Shift register
wire[32:0] col_shift  = (33'h1FFFFFFFE)<<col_intermediate_w;
wire[32:0] col_shift_inv;
generate
  for (i=0;i<33;i=i+1) begin
    assign col_shift_inv[i] = col_shift[32-i];
  end
endgenerate

//-COLUMN START VALUE OF SHIFT REGISTER because cell {0,0} is a Dummy-
// row  col  | first row   other rows
// 0    0    | 10..00      10..00 
// 0    1    | 00..00      10..00
// 1    0    | 00..00      00..00
// 1    1    | 00..00      00..00

wire zeroes = row_mode == 1'b1 | (row_mode==1'b0 & col_mode==1'b1 & is_first_row );

wire[31:0] col_even_n = zeroes ? col_shift[32:1] : col_shift[31:0];
wire[31:0] col_odd_n  = zeroes ? col_shift_inv[31:0] :
                                 col_shift_inv[32:1] ;

/// Column-Side-to-Side mode
wire[31:0] col_sidetoside_n = row_direction_RL ? col_odd_n : col_even_n;

/// Column Middle-to-Side mode
wire[31:0] col_midtoside_n;
generate
  for (i=0;i<16;i=i+1) begin
    assign col_midtoside_n[16+i] = col_even_n[2*i];
    assign col_midtoside_n[15-i] = col_even_n[2*i+1];
  end
endgenerate
/// Column Out
assign col_out_n = col_mode ? col_midtoside_n : col_sidetoside_n;
assign col_out = ~col_out_n;                            


// *********************************************
//   Bincap decoder, C0 decoder, misc
// *********************************************
assign bincap_out_n = ~bincap_w;

// semi-differential wires
assign rowoff_out_n = ~(row_out_n&rowon_out_n);

// LSB capacitor C0 is always enabled or disabled
assign c0p_out_n = 1'b0;
assign c0n_out_n = 1'b1;

endmodule



