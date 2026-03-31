`timescale 1ns/1ps

module sub_verification(                   //(always a>b and a n b must be bcd)
    input clk,
    input rst,
    input [3:0] a,b,
    output [3:0] ds_sub);
   
    wire [3:0] ds_a,ds_b;
   
    digit_sum_bc #(4) DS_A  (clk,rst,a,ds_a);  //single digit of a
    digit_sum_bc #(4) DS_B  (clk,rst,b,ds_b);  //single digit of b
       

   
    wire [3:0] sub;
   
    assign sub=ds_a-ds_b;
   
   
    digit_sum_bc #(4) DS_S  (clk,rst,sub, ds_sub);//single digit of b
   
endmodule






module digit_sum_bc                                        
 #(                                                        
    parameter WIDTH = 16                                  
)(  input clk,
    input rst,                                                      
    input  [WIDTH-1:0] in,  
    output reg [3:0] ds                                    
);                                                        
                                                           
    reg [3:0] tens, ones;                                  
                                                           
    always @(*) begin                                      
        tens = 4'b0000;                                    
        ones = 4'b0000;                                    
        ds   = 4'b0000;                                    
                                                           
        // Fast path: 0?8                                  
                                                           
                                                           
            // BCD separation                
            if (in < 16'd10) begin            // 9        
                tens = 4'b0000;                            
                ones = in[3:0];                            
            end                                            
            else if (in < 16'd20) begin       // 10-19    
                tens = 4'b0001;                            
                ones = in - 16'd10;                        
            end                                            
            else if (in < 16'd30) begin       // 20-29    
                tens = 4'b0010;                            
                ones = in - 16'd20;                        
            end                                            
            else if (in < 16'd40) begin       // 30-39    
                tens = 4'b0011;                            
                ones = in - 16'd30;                        
            end                                            
            else if (in < 16'd50) begin       // 40-49    
                tens = 4'b0100;                            
                ones = in - 16'd40;                        
                                                           
                                                           
            end                                            
            else if (in < 16'd60) begin       // 40-49    
                tens = 4'b0101;                            
                ones = in - 16'd50;                        
            end                                            
            else begin                        // 50-60    
                tens = 4'b0110;                            
                ones = in - 16'd60;                        
            end                                            
                                                           
                                                           
            // Digit sum (max = 5 + 9 = 14)                
            ds = tens + ones;                              
                                                           
             // Final reduction to single digit            
    if (ds >= 10)                                          
        ds = ds - 9;                                      
        end                                                
                                                           
                                                           
endmodule



module adder_verification(
    input clk,
    input rst,
    input  [3:0]a,
    input  [3:0]b,
output [3:0]sum
);
    wire [3:0]ds_a,ds_b;
    wire [4:0] add;   // max width
 

    digit_sum_bc #(4) DS_A(clk,rst,a,ds_a);
    digit_sum_bc #(4) DS_B(clk,rst,b,ds_b);
   

    assign add =ds_a+ds_b;    

    digit_sum_bc #(5) DS_EXP(clk,rst,add,sum);

endmodule




module mul_verification(
    input clk,
    input rst,
    input [3:0]a,
    input [3:0]b,
   
    output [3:0]ds_product
);
    wire [3:0]ds_a, ds_b;
    wire [7:0]prod_ds_mul;
   

   
    digit_sum_bc #(4)  DS_A  (clk,rst,a,ds_a);
    digit_sum_bc #(4)  DS_B  (clk,rst,b,ds_b);
   

    // multiply
    assign prod_ds_mul=ds_a *ds_b;  

   
    digit_sum_bc #(8) DS_EXP (clk,rst,prod_ds_mul,ds_product);

   

endmodule





module div_verification(
    input clk,
    input rst,
   input [3:0]a,  //divisor
    input [3:0]d, //dividend
    output [3:0]ds_q
);
    wire [3:0]ds_d, ds_a;
    wire [3:0] q;
   
   
// here input both are bcd and only the quotient is taken out
   
    digit_sum_bc #(4) DS_D  (clk,rst,d,ds_d);  //single digit of dividend
    digit_sum_bc #(4) DS_A  (clk,rst,a,ds_a);  //single digit of divisor
 


    assign q = (ds_a != 0) ? (ds_d / ds_a) : 4'd0;

    digit_sum_bc #(4) DS_aq (clk,rst,q,ds_q);
       
   

endmodule







module cmp_verification(
    input clk,
    input rst,
    input  [3:0] actual,   // from IO / real output
    input  [3:0] verify,   // already digit-sum reduced
    output        pass
);
    wire [3:0] ds_actual;

    // Digit sum only for actual output
    digit_sum_bc #(4) DS_ACT (.clk(clk),.rst(rst),
        .in(actual),
        .ds(ds_actual)
    );

    // 1 = match, 0 = mismatch
    assign pass = (ds_actual == verify);

endmodule



module d_ff(
input clk,
input reset,
input [3:0]d,
output reg [3:0]q);

always @(posedge clk or posedge reset)
begin
if (reset)
q<=4'd0;
else
q<=d;
end
endmodule


//2 inputs to tile

module cb_2in_generic #(
    parameter DW = 4,
    parameter integer TRACKS = 16,
    parameter integer T0 = 0,
    parameter integer T1 = 1,
    parameter integer T2 = 2,
    parameter integer T3 = 3
)(
    input  [63:0] track_bus,//16 tracks with 4 bit width each
    input  [1:0]  sel0,//selection line for input 1(2 bit)
    input  [1:0]  sel1,//selection line for input 2(2 bit)
    output reg [DW-1:0] in0,//(4 bits)
    output reg [DW-1:0] in1
);

    localparam integer I0 = T0 % TRACKS;
    localparam integer I1 = T1 % TRACKS;
    localparam integer I2 = T2 % TRACKS;
    localparam integer I3 = T3 % TRACKS;

    wire [DW-1:0] t0 = track_bus[I0*DW +: DW];
    wire [DW-1:0] t1 = track_bus[I1*DW +: DW];
    wire [DW-1:0] t2 = track_bus[I2*DW +: DW];
    wire [DW-1:0] t3 = track_bus[I3*DW +: DW];

    always @(*) begin
        case (sel0)
            2'd0: in0 = t0;
            2'd1: in0 = t1;
            2'd2: in0 = t2;
            2'd3: in0 = t3;
            default: in0 = 4'b0;
        endcase

        case (sel1)
            2'd0: in1 = t0;
            2'd1: in1 = t1;
            2'd2: in1 = t2;
            2'd3: in1 = t3;
            default: in1 = 4'b0;
        endcase
    end

endmodule

//ff
module cb_1in_generic #(
    parameter DW = 4,
    parameter integer TRACKS = 16,
    parameter integer T0 = 0,
    parameter integer T1 = 1,
    parameter integer T2 = 2,
    parameter integer T3 = 3
)(
    input  [63:0] track_bus,
    input  [1:0]  sel,
    output reg [DW-1:0] in0
);

    localparam integer I0 = T0 % TRACKS;
    localparam integer I1 = T1 % TRACKS;
    localparam integer I2 = T2 % TRACKS;
    localparam integer I3 = T3 % TRACKS;

   
    wire [DW-1:0] t0 = track_bus[I0*DW +: DW];
    wire [DW-1:0] t1 = track_bus[I1*DW +: DW];
    wire [DW-1:0] t2 = track_bus[I2*DW +: DW];
    wire [DW-1:0] t3 = track_bus[I3*DW +: DW];

    always @(*) begin
        case (sel)
            2'd0: in0 = t0;
            2'd1: in0 = t1;
            2'd2: in0 = t2;
            2'd3: in0 = t3;
            default: in0 = 4'b0;
        endcase
    end

endmodule

//tile to track
module cb_1out_generic #(
    parameter DW = 4,
    parameter integer TRACKS = 16,
    parameter integer T0 = 0,
    parameter integer T1 = 1,
    parameter integer T2 = 2,
    parameter integer T3 = 3
)(
    input  [DW-1:0] tile_out,              // output from tile
    input  [1:0]    sel,                   // selects which track to drive
    output reg [TRACKS*DW-1:0] track_drive // drives ONE of the tracks
);

 
    localparam integer I0 = T0 % TRACKS;
    localparam integer I1 = T1 % TRACKS;
    localparam integer I2 = T2 % TRACKS;
    localparam integer I3 = T3 % TRACKS;

    integer i;

    always @(*) begin
       
        track_drive = 64'b0;

        // Drive one selected track
        case (sel)
            2'd0: track_drive[I0*DW +: DW] = tile_out;
            2'd1: track_drive[I1*DW +: DW] = tile_out;
            2'd2: track_drive[I2*DW +: DW] = tile_out;
            2'd3: track_drive[I3*DW +: DW] = tile_out;
            default: track_drive[I0*DW +: DW] = tile_out;
        endcase
    end

endmodule



module io_block #(
    parameter DW = 4,
    parameter integer TRACKS = 16,
    parameter integer T0 = 0,
    parameter integer T1 = 1,
    parameter integer T2 = 2,
    parameter integer T3 = 3
)(
    input  [DW-1:0] io_in,//4bits
    input  [1:0]    sel,//2 bits
    output reg [TRACKS*DW-1:0] track_drive //63:0
);
 //ranges from 0 -> 15
 //track index belongs to [0 ? TRACKS-1]

    localparam integer I0 = T0 % TRACKS;
    localparam integer I1 = T1 % TRACKS;
    localparam integer I2 = T2 % TRACKS;
    localparam integer I3 = T3 % TRACKS;

    always @(*) begin
        track_drive = 64'b0;
        case (sel)
            2'd0: track_drive[I0*DW +: DW] = io_in;
            2'd1: track_drive[I1*DW +: DW] = io_in;
            2'd2: track_drive[I2*DW +: DW] = io_in;
            2'd3: track_drive[I3*DW +: DW] = io_in;
            default: track_drive[I3*DW +: DW] = io_in;
        endcase
    end

endmodule



module switch_block #(
    parameter integer TRACKS = 16,
    parameter integer DW     = 4
)(
    input  [TRACKS*DW-1:0] tracks_in,//64 bit
    input  [TRACKS*2-1:0]  cfg,//32 bit vector containing 2 bit select lines for each track
    output reg [TRACKS*DW-1:0] tracks_out//64 bit
);

    integer i;

    // Pre-compute wrapped indices (constant)
    function integer wrap;
        input integer val;
        begin
            wrap = (val < TRACKS) ? val : (val - TRACKS);
        end
    endfunction
//wrap is for selection of track,it does not allow the track to exceed 16 (0->15)
//cfg is for direction purpose (each diris of 2 bits) (str-00, 01-r8, 10-left, 11-disgonal)

    always @(*) begin
        tracks_out = 64'b0;

        for (i = 0; i < TRACKS; i = i + 1) begin
            case (cfg[i*2 +: 2])
                2'd0: tracks_out[i*DW +: DW] =
                      tracks_in[wrap(i+0)*DW +: DW];
                2'd1: tracks_out[i*DW +: DW] =
                      tracks_in[wrap(i+1)*DW +: DW];
                2'd2: tracks_out[i*DW +: DW] =
                      tracks_in[wrap(i+2)*DW +: DW];
2'd3: tracks_out[i*DW +: DW] = tracks_in[wrap(i+3)*DW +: DW];
                default:
                      tracks_out[i*DW +: DW] = tracks_in[wrap(i+3)*DW +: DW];
                     
            endcase
        end
    end
endmodule








module verification_fabric_top (
    input         clk,
    input         rst,

    // SWITCH BLOCK CONFIG
    // 25 SB Ã— 32 bits x 6paths = 800 bits
    input [4799:0] cfg_sb,

    input  [79:0] io_in,       // 20 IO Ã— 4 bits
    input  [39:0] cfg_io_sel,  // 20 IO Ã— 2 bits

 
    // MULTIPLIER
    input  [19:0] cfg_mul_in0,
    input  [19:0] cfg_mul_in1,
    input  [19:0] cfg_mul_out,

    // ADDER
    input  [19:0] cfg_add_in0,
    input  [19:0] cfg_add_in1,
    input  [19:0] cfg_add_out,

    // SUBTRACTOR
    input  [5:0]  cfg_sub_in0,
    input  [5:0]  cfg_sub_in1,
    input  [5:0]  cfg_sub_out,

    // DIVIDER
    input  [3:0]  cfg_div_in0,
    input  [3:0]  cfg_div_in1,
    input  [3:0]  cfg_div_out,

    // FLIP-FLOP
    input  [19:0] cfg_ff_in,
    input  [19:0] cfg_ff_out,

    // COMPARATOR
    input  [1:0]  cfg_cmp_in0,
    input  [1:0]  cfg_cmp_in1,
output [3:0] io_out
);



wire [383:0] sb_to_hc;
wire [383:0] sb_to_vc;
// ROUTING CHANNELS

wire [383:0] HC;   // 6 Ã— 64 bits Horizontal channels
wire [383:0] VC;   // 6 Ã— 64 bits Vertical channels
wire [63:0] hc0_from_io;
wire [63:0] hc0_from_sb;
wire [63:0] hc0_from_tiles;
wire [63:0] hc5_from_io;
wire [63:0] hc5_from_sb;
wire [63:0] hc5_from_tiles;
wire [63:0] vc5_from_io;
wire [63:0] vc5_from_sb;
wire [63:0] vc5_from_tiles;
wire [63:0] vc0_from_io;
wire [63:0] vc0_from_sb;
wire [63:0] vc0_from_tiles;
wire [63:0] vc1_from_tiles;
wire [63:0] vc1_from_sb;
wire [63:0] vc2_from_tiles;
wire [63:0] vc2_from_sb;
wire [63:0] vc3_from_tiles;
wire [63:0] vc3_from_sb;
wire [63:0] vc4_from_tiles;
wire [63:0] vc4_from_sb;
wire [63:0] hc1_from_tiles;
wire [63:0] hc1_from_sb;
wire [63:0] hc2_from_tiles;
wire [63:0] hc2_from_sb;
wire [63:0] hc3_from_tiles;
wire [63:0] hc3_from_sb;
wire [63:0] hc4_from_tiles;
wire [63:0] hc4_from_sb;
    // IO BLOCKS(20)

    // Track drives from IO blocks
    wire [63:0] io_d0,  io_d1,  io_d2,  io_d3,  io_d4;
    wire [63:0] io_d5,  io_d6,  io_d7,  io_d8,  io_d9;
    wire [63:0] io_d10, io_d11, io_d12, io_d13, io_d14;
    wire [63:0] io_d15, io_d16, io_d17, io_d18, io_d19;


    io_block IO0  (.io_in(io_in[ 3: 0]), .sel(cfg_io_sel[ 1: 0]), .track_drive(io_d0));
    io_block IO1  (.io_in(io_in[ 7: 4]), .sel(cfg_io_sel[ 3: 2]), .track_drive(io_d1));
    io_block IO2  (.io_in(io_in[11: 8]), .sel(cfg_io_sel[ 5: 4]), .track_drive(io_d2));
    io_block IO3  (.io_in(io_in[15:12]), .sel(cfg_io_sel[ 7: 6]), .track_drive(io_d3));
    io_block IO4  (.io_in(io_in[19:16]), .sel(cfg_io_sel[ 9: 8]), .track_drive(io_d4));

    io_block IO5  (.io_in(io_in[23:20]), .sel(cfg_io_sel[11:10]), .track_drive(io_d5));
    io_block IO6  (.io_in(io_in[27:24]), .sel(cfg_io_sel[13:12]), .track_drive(io_d6));
    io_block IO7  (.io_in(io_in[31:28]), .sel(cfg_io_sel[15:14]), .track_drive(io_d7));
    io_block IO8  (.io_in(io_in[35:32]), .sel(cfg_io_sel[17:16]), .track_drive(io_d8));
    io_block IO9  (.io_in(io_in[39:36]), .sel(cfg_io_sel[19:18]), .track_drive(io_d9));

    io_block IO10 (.io_in(io_in[43:40]), .sel(cfg_io_sel[21:20]), .track_drive(io_d10));
    io_block IO11 (.io_in(io_in[47:44]), .sel(cfg_io_sel[23:22]), .track_drive(io_d11));
    io_block IO12 (.io_in(io_in[51:48]), .sel(cfg_io_sel[25:24]), .track_drive(io_d12));
    io_block IO13 (.io_in(io_in[55:52]), .sel(cfg_io_sel[27:26]), .track_drive(io_d13));
    io_block IO14 (.io_in(io_in[59:56]), .sel(cfg_io_sel[29:28]), .track_drive(io_d14));

    io_block IO15 (.io_in(io_in[63:60]), .sel(cfg_io_sel[31:30]), .track_drive(io_d15));
    io_block IO16 (.io_in(io_in[67:64]), .sel(cfg_io_sel[33:32]), .track_drive(io_d16));
    io_block IO17 (.io_in(io_in[71:68]), .sel(cfg_io_sel[35:34]), .track_drive(io_d17));
    io_block IO18 (.io_in(io_in[75:72]), .sel(cfg_io_sel[37:36]), .track_drive(io_d18));
    io_block IO19 (.io_in(io_in[79:76]), .sel(cfg_io_sel[39:38]), .track_drive(io_d19));


assign hc0_from_io = io_d0 | io_d1 | io_d2 | io_d3 | io_d4;
assign vc5_from_io =   io_d5  | io_d6  | io_d7  | io_d8  | io_d9;
assign vc0_from_io = io_d15 | io_d16 | io_d17 | io_d18 | io_d19;
assign hc5_from_io =   io_d10 | io_d11 | io_d12 | io_d13 | io_d14;

// SWITCH BLOCKS (25)

   
genvar r, c;
generate
  for (r = 0; r < 5; r = r + 1) begin : SB_ROW
    for (c = 0; c < 5; c = c + 1) begin : SB_COL

      localparam integer SB_BASE = (r*5 + c) * 6 * 32;

      switch_block SB_HC_VC (
        .tracks_in  ( HC[(c*64)+63 : c*64] ),
        .cfg        ( cfg_sb[SB_BASE +  0 +: 32] ),
        .tracks_out ( sb_to_vc[(r*64)+63 : r*64] )
      );

      switch_block SB_VC_HC (
        .tracks_in  ( VC[(r*64)+63 : r*64] ),
        .cfg        ( cfg_sb[SB_BASE + 32 +: 32] ),
        .tracks_out ( sb_to_hc[(c*64)+63 : c*64] )
      );

      switch_block SB_HC_HC (
        .tracks_in  ( HC[(c*64)+63 : c*64] ),
        .cfg        ( cfg_sb[SB_BASE + 64 +: 32] ),
        .tracks_out ( sb_to_hc[((c+1)*64)+63 : (c+1)*64] )
      );

      switch_block SB_VC_VC (
        .tracks_in  ( VC[(r*64)+63 : r*64] ),
        .cfg        ( cfg_sb[SB_BASE + 96 +: 32] ),
        .tracks_out ( sb_to_vc[((r+1)*64)+63 : (r+1)*64] )
      );

      switch_block SB_HC_VC_D (
        .tracks_in  ( HC[(c*64)+63 : c*64] ),
        .cfg        ( cfg_sb[SB_BASE +128 +: 32] ),
        .tracks_out ( sb_to_vc[((r+1)*64)+63 : (r+1)*64] )
      );

      switch_block SB_VC_HC_R (
        .tracks_in  ( VC[(r*64)+63 : r*64] ),
        .cfg        ( cfg_sb[SB_BASE +160 +: 32] ),
        .tracks_out ( sb_to_hc[((c+1)*64)+63 : (c+1)*64] )
      );

    end
  end
endgenerate
assign hc0_from_sb = sb_to_hc[63:0];
assign hc1_from_sb = sb_to_hc[127:64];
assign hc2_from_sb = sb_to_hc[191:128];
assign hc3_from_sb = sb_to_hc[255:192];
assign hc4_from_sb = sb_to_hc[319:256];
assign hc5_from_sb = sb_to_hc[383:320];

assign vc0_from_sb = sb_to_vc[63:0];
assign vc1_from_sb = sb_to_vc[127:64];
assign vc2_from_sb = sb_to_vc[191:128];
assign vc3_from_sb = sb_to_vc[255:192];
assign vc4_from_sb = sb_to_vc[319:256];
assign vc5_from_sb = sb_to_vc[383:320];



 
// TILE 1 (MUL1)
wire [3:0] t0_a, t0_b, t0_out;
wire [63:0] t0_drive;
cb_2in_generic  #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T0_IN(
    .track_bus ( VC[(0*64)+63 : 0*64] ), // VC0
    .sel0      ( cfg_mul_in0[1:0] ),
    .sel1      ( cfg_mul_in1[1:0] ),
    .in0       ( t0_a ),
    .in1       ( t0_b )
);

mul_verification M0 (
    .clk(clk),
    .rst(rst),
    .a(t0_a),
    .b(t0_b),
    .ds_product(t0_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    ) CB_T0_OUT(
    .tile_out   ( t0_out ),
    .sel        ( cfg_mul_out[1:0] ),
    .track_drive( t0_drive )
);

// drive HC0
//assign HC[(0*64)+63 : 0*64] = t0_drive;







// TILE 5 (MUL2)
wire [3:0] t5_a, t5_b, t5_out;
wire [63:0] t5_drive;
cb_2in_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T5_IN(
    .track_bus ( VC[(0*64)+63 : 0*64] ), // VC0
    .sel0      ( cfg_mul_in0[3:2] ),
    .sel1      ( cfg_mul_in1[3:2] ),
    .in0       ( t5_a ),
    .in1       ( t5_b )
);

mul_verification M5 (
    .clk(clk),
    .rst(rst),
    .a(t5_a),
    .b(t5_b),
    .ds_product(t5_out)
);

cb_1out_generic#(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )  CB_T5_OUT(
    .tile_out   ( t5_out ),
    .sel        ( cfg_mul_out[3:2]  ),
    .track_drive( t5_drive )
);

// drive HC5
//assign HC[(5*64)+63 : 5*64] = t5_drive;


// TILE 7 (MUL3)
wire [3:0] t7_a, t7_b, t7_out;
wire [63:0] t7_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T7_IN(
    .track_bus ( VC[(1*64)+63 : 1*64] ), // VC1
    .sel0      ( cfg_mul_in0[5:4] ),
    .sel1      ( cfg_mul_in1[5:4] ),
    .in0       ( t7_a ),
    .in1       ( t7_b )
);

mul_verification M7 (
    .clk(clk),
    .rst(rst),
    .a(t7_a),
    .b(t7_b),
    .ds_product(t7_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    ) CB_T7_OUT(
    .tile_out   ( t7_out ),
    .sel        ( cfg_mul_out[5:4]  ),
    .track_drive( t7_drive )
);

// drive HC1
//assign HC[(1*64)+63 : 1*64] = t7_drive;



// TILE 10 (MUL4)
wire [3:0] t10_a, t10_b, t10_out;
wire [63:0] t10_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T10_IN(
    .track_bus ( VC[(1*64)+63 : 1*64] ), // VC0
    .sel0      ( cfg_mul_in0[7:6] ),
    .sel1      ( cfg_mul_in1[7:6] ),
    .in0       ( t10_a ),
    .in1       ( t10_b )
);

mul_verification M10 (
    .clk(clk),
    .rst(rst),
    .a(t10_a),
    .b(t10_b),
    .ds_product(t10_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T10_OUT (
    .tile_out   ( t10_out ),
    .sel        ( cfg_mul_out[7:6]  ),
    .track_drive( t10_drive )
);

// drive HC4
//assign HC[(4*64)+63 : 4*64] = t10_drive;


// TILE 15 (MUL5)
wire [3:0] t15_a, t15_b, t15_out;
wire [63:0] t15_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T15_IN(
    .track_bus ( VC[(2*64)+63 : 2*64] ), // VC2
    .sel0      ( cfg_mul_in0[9:8] ),
    .sel1      ( cfg_mul_in1[9:8] ),
    .in0       ( t15_a ),
    .in1       ( t15_b )
);

mul_verification M15 (
    .clk(clk),
    .rst(rst),
    .a(t15_a),
    .b(t15_b),
    .ds_product(t15_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T15_OUT (
    .tile_out   ( t15_out ),
    .sel        ( cfg_mul_out[9:8]  ),
    .track_drive( t15_drive )
);

// drive HC3
//assign HC[(3*64)+63 : 3*64] = t15_drive;


// TILE 17 (MUL6)
wire [3:0] t17_a, t17_b, t17_out;
wire [63:0] t17_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T17_IN(
    .track_bus ( VC[(2*64)+63 : 2*64] ), // VC2
    .sel0      ( cfg_mul_in0[11:10] ),
    .sel1      ( cfg_mul_in1[11:10] ),
    .in0       ( t17_a ),
    .in1       ( t17_b )
);

mul_verification M17 (
    .clk(clk),
    .rst(rst),
    .a(t17_a),
    .b(t17_b),
    .ds_product(t17_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    ) CB_T17_OUT(
    .tile_out   ( t17_out ),
    .sel        ( cfg_mul_out[11:10]  ),
    .track_drive( t17_drive )
);

// drive HC5
//assign HC[(5*64)+63 : 5*64] = t17_drive;


// TILE 19 (MUL7)
wire [3:0] t19_a, t19_b, t19_out;
wire [63:0] t19_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T19_IN(
    .track_bus ( VC[(3*64)+63 : 3*64] ), // VC3
    .sel0      ( cfg_mul_in0[13:12] ),
    .sel1      ( cfg_mul_in1[13:12] ),
    .in0       ( t19_a ),
    .in1       ( t19_b )
);

mul_verification M19 (
    .clk(clk),
    .rst(rst),
    .a(t19_a),
    .b(t19_b),
    .ds_product(t19_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T19_OUT (
    .tile_out   ( t19_out ),
    .sel        ( cfg_mul_out[13:12]  ),
    .track_drive( t19_drive )
);

// drive HC1
//assign HC[(1*64)+63 : 1*64] = t19_drive;


// TILE 24 (MUL8)
wire [3:0] t24_a, t24_b, t24_out;
wire [63:0] t24_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T24_IN(
    .track_bus ( VC[(4*64)+63 : 4*64] ), // VC4
    .sel0      ( cfg_mul_in0[15:14] ),
    .sel1      ( cfg_mul_in1[15:14] ),
    .in0       ( t24_a ),
    .in1       ( t24_b )
);

mul_verification M24 (
    .clk(clk),
    .rst(rst),
    .a(t24_a),
    .b(t24_b),
    .ds_product(t24_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    ) CB_T24_OUT(
    .tile_out   ( t24_out ),
    .sel        ( cfg_mul_out[15:14] ),
    .track_drive( t24_drive )
);

// drive HC0
//assign HC[(0*64)+63 : 0*64] = t24_drive;


// TILE 29 (MUL9)
wire [3:0] t29_a, t29_b, t29_out;
wire [63:0] t29_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T29_IN(
    .track_bus ( VC[(4*64)+63 : 4*64] ), // VC4
    .sel0      ( cfg_mul_in0[17:16] ),
    .sel1      ( cfg_mul_in1[17:16] ),
    .in0       ( t29_a ),
    .in1       ( t29_b )
);

mul_verification M29 (
    .clk(clk),
    .rst(rst),
    .a(t29_a),
    .b(t29_b),
    .ds_product(t29_out)
);

cb_1out_generic#(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )  CB_T29_OUT(
    .tile_out   ( t29_out ),
    .sel        ( cfg_mul_out[17:16] ),
    .track_drive( t29_drive )
);

// drive HC5
//assign HC[(5*64)+63 : 5*64] = t29_drive;



// TILE 31 (MUL10)
wire [3:0] t31_a, t31_b, t31_out;
wire [63:0] t31_drive;
cb_2in_generic   #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T31_IN(
    .track_bus ( VC[(5*64)+63 : 5*64] ), // VC5
    .sel0      ( cfg_mul_in0[19:18] ),
    .sel1      ( cfg_mul_in1[19:18] ),
    .in0       ( t31_a ),
    .in1       ( t31_b )
);

mul_verification M31 (
    .clk(clk),
    .rst(rst),
    .a(t31_a),
    .b(t31_b),
    .ds_product(t31_out)
);

cb_1out_generic #(
        .T0(1), .T1(2), .T2(3), .T3(4)
    )CB_T31_OUT(
    .tile_out   ( t31_out ),
    .sel        ( cfg_mul_out[19:18] ),
    .track_drive( t31_drive )
);

// drive HC1
//assign HC[(1*64)+63 : 1*64] = t31_drive;







// TILE 1 (ADD1)
wire [3:0] t1_a, t1_b, t1_out;
wire [63:0] t1_drive;
cb_2in_generic   #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T1_IN(
    .track_bus ( VC[(0*64)+63 : 0*64] ), // VC0
    .sel0      ( cfg_add_in0[1:0] ),
    .sel1      ( cfg_add_in1[1:0] ),
    .in0       ( t1_a ),
    .in1       ( t1_b )
);

adder_verification ADD1 (
                .clk(clk),
                .rst(rst),
                .a(t1_a),
                .b(t1_b),
                .sum(t1_out)
            );


cb_1out_generic #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    ) CB_T1_OUT(
    .tile_out   ( t1_out ),
    .sel        ( cfg_add_out[1:0] ),
    .track_drive( t1_drive )
);

// drive HC1
//assign HC[(1*64)+63 : 1*64] = t1_drive;




// TILE 6 (ADD2)
wire [3:0] t6_a, t6_b, t6_out;
wire [63:0] t6_drive;
cb_2in_generic   #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T6_IN(
    .track_bus ( VC[(1*64)+63 : 1*64] ), // VC1
    .sel0      ( cfg_add_in0[3:2] ),
    .sel1      ( cfg_add_in1[3:2] ),
    .in0       ( t6_a ),
    .in1       ( t6_b )
);

adder_verification ADD2 (
                .clk(clk),
                .rst(rst),
                .a(t6_a),
                .b(t6_b),
                .sum(t6_out)
            );


cb_1out_generic #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T6_OUT (
    .tile_out   ( t6_out ),
    .sel        ( cfg_add_out[3:2]  ),
    .track_drive( t6_drive )
);

// drive HC0
//assign HC[(0*64)+63 : 0*64] = t6_drive;


// TILE 8 (ADD3)
wire [3:0] t8_a, t8_b, t8_out;
wire [63:0] t8_drive;
cb_2in_generic   #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T8_IN(
    .track_bus ( VC[(1*64)+63 : 1*64] ), // VC1
    .sel0      ( cfg_add_in0[5:4] ),
    .sel1      ( cfg_add_in1[5:4] ),
    .in0       ( t8_a ),
    .in1       ( t8_b )
);

adder_verification ADD3 (
                .clk(clk),
                .rst(rst),
                .a(t8_a),
                .b(t8_b),
                .sum(t8_out)
            );


cb_1out_generic #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T8_OUT(
    .tile_out   ( t8_out ),
    .sel        ( cfg_add_out[5:4]  ),
    .track_drive( t8_drive )
);

// drive HC2
//assign HC[(2*64)+63 : 2*64] = t8_drive;



// TILE 11 (ADD4)
wire [3:0] t11_a, t11_b, t11_out;
wire [63:0] t11_drive;
cb_2in_generic   #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T11_IN(
    .track_bus ( VC[(1*64)+63 : 1*64] ), // VC1
    .sel0      ( cfg_add_in0[7:6] ),
    .sel1      ( cfg_add_in1[7:6] ),
    .in0       ( t11_a ),
    .in1       ( t11_b )
);
adder_verification ADD4 (
                .clk(clk),
                .rst(rst),
                .a(t11_a),
                .b(t11_b),
                .sum(t11_out)
            );

cb_1out_generic#(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )  CB_T11_OUT(
    .tile_out   ( t11_out ),
    .sel        ( cfg_add_out[7:6]  ),
    .track_drive( t11_drive )
);

// drive HC4
//assign HC[(5*64)+63 : 5*64] = t11_drive;


// TILE 18 (ADD5)
wire [3:0] t18_a, t18_b, t18_out;
wire [63:0] t18_drive;
cb_2in_generic  #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T18_IN (
    .track_bus ( VC[(3*64)+63 : 3*64] ), // VC3
    .sel0      ( cfg_add_in0[9:8] ),
    .sel1      ( cfg_add_in1[9:8] ),
    .in0       ( t18_a ),
    .in1       ( t18_b )
);

adder_verification ADD5 (
                .clk(clk),
                .rst(rst),
                .a(t18_a),
                .b(t18_b),
                .sum(t18_out)
            );


cb_1out_generic #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T18_OUT(
    .tile_out   ( t18_out ),
    .sel        ( cfg_add_out[9:8]  ),
    .track_drive( t18_drive )
);

// drive HC0
//assign HC[(0*64)+63 : 0*64] = t18_drive;


// TILE 20 (ADD6)
wire [3:0] t20_a, t20_b, t20_out;
wire [63:0] t20_drive;
cb_2in_generic   #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T20_IN(
    .track_bus ( VC[(3*64)+63 : 3*64] ), // VC3
    .sel0      ( cfg_add_in0[11:10] ),
    .sel1      ( cfg_add_in1[11:10] ),
    .in0       ( t20_a ),
    .in1       ( t20_b )
);
adder_verification ADD6 (
                .clk(clk),
                .rst(rst),
                .a(t20_a),
                .b(t20_b),
                .sum(t20_out)
            );


cb_1out_generic #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T20_OUT(
    .tile_out   ( t20_out ),
    .sel        ( cfg_add_out[11:10]  ),
    .track_drive( t20_drive )
);

// drive HC2
//assign HC[(2*64)+63 : 2*64] = t20_drive;


// TILE 22 (ADD7)
wire [3:0] t22_a, t22_b, t22_out;
wire [63:0] t22_drive;
cb_2in_generic   #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T22_IN(
    .track_bus ( VC[(3*64)+63 : 3*64] ), // VC3
    .sel0      ( cfg_add_in0[13:12] ),
    .sel1      ( cfg_add_in1[13:12] ),
    .in0       ( t22_a ),
    .in1       ( t22_b )
);

adder_verification ADD22 (
                .clk(clk),
                .rst(rst),
                .a(t22_a),
                .b(t22_b),
                .sum(t22_out)
            );

cb_1out_generic #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    ) CB_T22_OUT(
    .tile_out   ( t22_out ),
    .sel        ( cfg_add_out[13:12]  ),
    .track_drive( t22_drive )
);

// drive HC4
//assign HC[(4*64)+63 : 4*64] = t22_drive;


// TILE 25 (ADD8)
wire [3:0] t25_a, t25_b, t25_out;
wire [63:0] t25_drive;
cb_2in_generic  #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T25_IN(
    .track_bus ( VC[(4*64)+63 : 4*64] ), // VC4
    .sel0      ( cfg_add_in0[15:14] ),
    .sel1      ( cfg_add_in1[15:14] ),
    .in0       ( t25_a ),
    .in1       ( t25_b )
);

adder_verification ADD25 (
                .clk(clk),
                .rst(rst),
                .a(t25_a),
                .b(t25_b),
                .sum(t25_out)
            );

cb_1out_generic#(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )  CB_T25_OUT(
    .tile_out   ( t25_out ),
    .sel        ( cfg_add_out[15:14] ),
    .track_drive( t25_drive )
);

// drive HC1
//assign HC[(1*64)+63 : 1*64] = t25_drive;


// TILE 27 (ADD9)
wire [3:0] t27_a, t27_b, t27_out;
wire [63:0] t27_drive;
cb_2in_generic   #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T27_IN(
    .track_bus ( VC[(4*64)+63 : 4*64] ), // VC4
    .sel0      ( cfg_add_in0[17:16] ),
    .sel1      ( cfg_add_in1[17:16] ),
    .in0       ( t27_a ),
    .in1       ( t27_b )
);
adder_verification ADD27 (
                .clk(clk),
                .rst(rst),
                .a(t27_a),
                .b(t27_b),
                .sum(t27_out)
            );


cb_1out_generic #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T27_OUT(
    .tile_out   ( t27_out ),
    .sel        ( cfg_add_out[17:16] ),
    .track_drive( t27_drive )
);

// drive HC3
//assign HC[(3*64)+63 : 3*64] = t27_drive;



// TILE 30 (ADD10)
wire [3:0] t30_a, t30_b, t30_out;
wire [63:0] t30_drive;
cb_2in_generic  #(
        .T0(5), .T1(6), .T2(7), .T3(8)
    )CB_T30_IN (
    .track_bus ( VC[(5*64)+63 : 5*64] ), // VC5
    .sel0      ( cfg_add_in0[19:18] ),
    .sel1      ( cfg_add_in1[19:18] ),
    .in0       ( t30_a ),
    .in1       ( t30_b )
);

adder_verification ADD30 (
                .clk(clk),
                .rst(rst),
                .a(t30_a),
                .b(t30_b),
                .sum(t30_out)
            );


cb_1out_generic#(
        .T0(5), .T1(6), .T2(7), .T3(8)
    ) CB_T30_OUT(
    .tile_out   ( t30_out ),
    .sel        ( cfg_add_out[19:18] ),
    .track_drive( t30_drive )
);

// drive HC0
//assign HC[(0*64)+63 : 0*64] = t30_drive;


// TILE 4 (ff1)
wire [3:0] ff4_d;
wire [3:0] ff4_q;
wire [63:0] ff4_drive;

cb_1in_generic CB_FF4_IN (
    .track_bus ( HC[(4*64)+63 : 4*64] ),  // HC4
    .sel       ( cfg_ff_in[1:0] ),        
    .in0       ( ff4_d )
);
d_ff FF4 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff4_d ),
    .q     ( ff4_q )
);
cb_1out_generic CB_FF4_OUT (
    .tile_out   ( ff4_q ),
    .sel        ( cfg_ff_out[1:0] ),  
    .track_drive( ff4_drive )
);
//assign VC[(0*64)+63 : 0*64] = ff4_drive;   // VC0



// TILE 9 (ff2)
wire [3:0] ff9_d;
wire [3:0] ff9_q;
wire [63:0] ff9_drive;

cb_1in_generic CB_FF9_IN (
    .track_bus ( HC[(3*64)+63 : 3*64] ),  // HC3
    .sel       ( cfg_ff_in[3:2] ),        
    .in0       ( ff9_d )
);
d_ff FF9 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff9_d ),
    .q     ( ff9_q )
);
cb_1out_generic CB_FF9_OUT (
    .tile_out   ( ff9_q ),
    .sel        ( cfg_ff_out[3:2] ),  
    .track_drive( ff9_drive )
);
//assign VC[(1*64)+63 : 1*64] = ff9_drive;   // VC1




// TILE 13 (ff3)
wire [3:0] ff13_d;
wire [3:0] ff13_q;
wire [63:0] ff13_drive;

cb_1in_generic CB_FF13_IN (
    .track_bus ( HC[(1*64)+63 : 1*64] ),  // HC1
    .sel       ( cfg_ff_in[5:4] ),        
    .in0       ( ff13_d )
);
d_ff FF13 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff13_d ),
    .q     ( ff13_q )
);
cb_1out_generic CB_FF13_OUT (
    .tile_out   ( ff13_q ),
    .sel        ( cfg_ff_out[5:4] ),  
    .track_drive( ff13_drive )
);
//assign VC[(2*64)+63 : 2*64] = ff13_drive;   // VC2


// TILE 16 (ff4)
wire [3:0] ff16_d;
wire [3:0] ff16_q;
wire [63:0] ff16_drive;

cb_1in_generic CB_FF16_IN (
    .track_bus ( HC[(4*64)+63 : 4*64] ),  // HC4
    .sel       ( cfg_ff_in[7:6] ),        
    .in0       ( ff16_d )
);
d_ff FF16 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff16_d ),
    .q     ( ff16_q )
);
cb_1out_generic CB_FF16_OUT (
    .tile_out   ( ff16_q ),
    .sel        ( cfg_ff_out[7:6] ),  
    .track_drive( ff16_drive )
);
//assign VC[(2*64)+63 : 2*64] = ff16_drive;   // VC2


// TILE 21 (ff5)
wire [3:0] ff21_d;
wire [3:0] ff21_q;
wire [63:0] ff21_drive;

cb_1in_generic CB_FF21_IN (
    .track_bus ( HC[(3*64)+63 : 3*64] ),  // HC3
    .sel       ( cfg_ff_in[9:8] ),        
    .in0       ( ff21_d )
);
d_ff FF21 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff21_d ),
    .q     ( ff21_q )
);
cb_1out_generic CB_FF21_OUT (
    .tile_out   ( ff21_q ),
    .sel        ( cfg_ff_out[9:8] ),  
    .track_drive( ff21_drive )
);
//assign VC[(3*64)+63 : 3*64] = ff21_drive;   // VC3


// TILE 23 (ff6)
wire [3:0] ff23_d;
wire [3:0] ff23_q;
wire [63:0] ff23_drive;

cb_1in_generic CB_FF23_IN (
    .track_bus ( HC[(5*64)+63 : 5*64] ),  // HC5
    .sel       ( cfg_ff_in[11:10] ),        
    .in0       ( ff23_d )
);
d_ff FF23 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff23_d ),
    .q     ( ff23_q )
);
cb_1out_generic CB_FF23_OUT (
    .tile_out   ( ff23_q ),
    .sel        ( cfg_ff_out[11:10] ),  
    .track_drive( ff23_drive )
);
//assign VC[(3*64)+63 : 3*64] = ff23_drive;   // VC3

// TILE 26 (ff7)
wire [3:0] ff26_d;
wire [3:0] ff26_q;
wire [63:0] ff26_drive;

cb_1in_generic CB_FF26_IN (
    .track_bus ( HC[(2*64)+63 : 2*64] ),  // HC2
    .sel       ( cfg_ff_in[13:12] ),        
    .in0       ( ff26_d )
);
d_ff FF26 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff26_d ),
    .q     ( ff26_q )
);
cb_1out_generic CB_FF26_OUT (
    .tile_out   ( ff26_q ),
    .sel        ( cfg_ff_out[13:12] ),  
    .track_drive( ff26_drive )
);
//assign VC[(4*64)+63 : 4*64] = ff26_drive;   // VC4



// TILE 28 (ff8)
wire [3:0] ff28_d;
wire [3:0] ff28_q;
wire [63:0] ff28_drive;

cb_1in_generic CB_FF28_IN (
    .track_bus ( HC[(4*64)+63 : 4*64] ),  // HC4
    .sel       ( cfg_ff_in[15:14] ),        
    .in0       ( ff28_d )
);
d_ff FF28 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff28_d ),
    .q     ( ff28_q )
);
cb_1out_generic CB_FF28_OUT (
    .tile_out   ( ff28_q ),
    .sel        ( cfg_ff_out[15:14] ),  
    .track_drive( ff28_drive )
);
//assign VC[(4*64)+63 : 4*64] = ff28_drive;   // VC4



// TILE 34 (ff9)
wire [3:0] ff34_d;
wire [3:0] ff34_q;
wire [63:0] ff34_drive;

cb_1in_generic CB_FF34_IN (
    .track_bus ( HC[(4*64)+63 : 4*64] ),  // HC4
    .sel       ( cfg_ff_in[17:16] ),        
    .in0       ( ff34_d )
);
d_ff FF34 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff34_d ),
    .q     ( ff34_q )
);
cb_1out_generic CB_FF34_OUT (
    .tile_out   ( ff34_q ),
    .sel        ( cfg_ff_out[17:16] ),  
    .track_drive( ff34_drive )
);
//assign VC[(5*64)+63 : 5*64] = ff34_drive;   // VC5





// TILE 35(ff10)
wire [3:0] ff35_d;
wire [3:0] ff35_q;
wire [63:0] ff35_drive;

cb_1in_generic CB_FF35_IN (
    .track_bus ( HC[(5*64)+63 : 5*64] ),  // HC5
    .sel       ( cfg_ff_in[19:18] ),        
    .in0       ( ff35_d )
);
d_ff FF35 (
    .clk   ( clk ),
    .reset ( rst ),
    .d     ( ff35_d ),
    .q     ( ff35_q )
);
cb_1out_generic CB_FF35_OUT (
    .tile_out   ( ff35_q ),
    .sel        ( cfg_ff_out[19:18] ),  
    .track_drive( ff35_drive )
);
//assign VC[(5*64)+63 : 5*64] = ff35_drive;   // VC5


// TILE 2(sub1)
wire [3:0] sub2_a;
wire [3:0] sub2_b;
wire [3:0] sub2_out;
wire [63:0] sub2_drive;

cb_2in_generic CB_SUB2_IN (
    .track_bus ( HC[(2*64)+63 : 2*64] ),   // HC2
    .sel0      ( cfg_sub_in0[1:0] ),        
    .sel1      ( cfg_sub_in1[1:0] ),        
    .in0       ( sub2_a ),
    .in1       ( sub2_b )
);
sub_verification SUB2 (
    .clk    ( clk ),
    .rst    ( rst ),
    .a      ( sub2_a ),
    .b      ( sub2_b ),
    .ds_sub ( sub2_out )
);


cb_1out_generic CB_SUB2_OUT (
    .tile_out    ( sub2_out ),
    .sel         ( cfg_sub_out[1:0] ),  
    .track_drive ( sub2_drive )
);

//assign VC[(0*64)+63 : 0*64] = sub2_drive;   // VC0



// TILE 14(sub2)
wire [3:0] sub14_a;
wire [3:0] sub14_b;
wire [3:0] sub14_out;
wire [63:0] sub14_drive;

cb_2in_generic CB_SUB14_IN (
    .track_bus ( HC[(2*64)+63 : 2*64] ),   // HC2
    .sel0      ( cfg_sub_in0[3:2] ),        
    .sel1      ( cfg_sub_in1[3:2] ),        
    .in0       ( sub14_a ),
    .in1       ( sub14_b )
);
sub_verification SUB14 (
    .clk    ( clk ),
    .rst    ( rst ),
    .a      ( sub14_a ),
    .b      ( sub14_b ),
    .ds_sub ( sub14_out )
);


cb_1out_generic CB_SUB14_OUT (
    .tile_out    ( sub14_out ),
    .sel         ( cfg_sub_out[3:2] ),  
    .track_drive ( sub14_drive )
);

//assign VC[(2*64)+63 : 2*64] = sub14_drive;   // VC2


// TILE 32(sub3)
wire [3:0] sub32_a;
wire [3:0] sub32_b;
wire [3:0] sub32_out;
wire [63:0] sub32_drive;

cb_2in_generic CB_SUB32_IN (
    .track_bus ( HC[(2*64)+63 : 2*64] ),   // HC2
    .sel0      ( cfg_sub_in0[5:4] ),        
    .sel1      ( cfg_sub_in1[5:4] ),        
    .in0       ( sub32_a ),
    .in1       ( sub32_b )
);
sub_verification SUB32 (
    .clk    ( clk ),
    .rst    ( rst ),
    .a      ( sub32_a ),
    .b      ( sub32_b ),
    .ds_sub ( sub32_out )
);


cb_1out_generic CB_SUB32_OUT (
    .tile_out    ( sub32_out ),
    .sel         ( cfg_sub_out[5:4] ),  
    .track_drive ( sub32_drive )
);

//assign VC[(5*64)+63 : 5*64] = sub32_drive;   // VC5

// DIV TILE 3
wire [3:0] div3_a;
wire [3:0] div3_d;
wire [3:0] div3_q;
wire [63:0] div3_drive;
cb_2in_generic CB_DIV3_IN (
    .track_bus ( HC[(3*64)+63 : 3*64] ),   // HC3
    .sel0      ( cfg_div_in0[1:0] ),        
    .sel1      ( cfg_div_in1[1:0] ),        
    .in0       ( div3_a ),
    .in1       ( div3_d )
);
div_verification DIV3 (
    .clk  ( clk ),
    .rst  ( rst ),
    .a    ( div3_a ),
    .d    ( div3_d ),
    .ds_q ( div3_q )
);

cb_1out_generic CB_DIV3_OUT (
    .tile_out    ( div3_q ),
    .sel         ( cfg_div_out[1:0] ),  
    .track_drive ( div3_drive )
);
//assign VC[(0*64)+63 : 0*64] = div3_drive;   // VC0


// DIV TILE 33
wire [3:0] div33_a;
wire [3:0] div33_d;
wire [3:0] div33_q;
wire [63:0] div33_drive;
cb_2in_generic CB_DIV33_IN (
    .track_bus ( HC[(3*64)+63 : 3*64] ),   // HC3
    .sel0      ( cfg_div_in0[3:2] ),        
    .sel1      ( cfg_div_in1[3:2] ),        
    .in0       ( div33_a ),
    .in1       ( div33_d )
);

div_verification DIV33 (
    .clk  ( clk ),
    .rst  ( rst ),
    .a    ( div33_a ),
    .d    ( div33_d ),
    .ds_q ( div33_q )
);
cb_1out_generic CB_DIV33_OUT (
    .tile_out    ( div33_q ),
    .sel         ( cfg_div_out[3:2] ),  
    .track_drive ( div33_drive )
);
//assign VC[(5*64)+63 : 5*64] = div33_drive;   // VC5



//CMP TILE
wire [3:0] cmp0_actual;
wire [3:0] cmp0_verify;
wire cmp0_pass;
wire [3:0] cmp0_pass_ext;
wire [63:0] cmp0_drive;

// Input CB
cb_2in_generic CB_CMP_IN (
    .track_bus ( VC[(2*64)+63 : 2*64] ),   // VC2
    .sel0      ( cfg_cmp_in0 ),
    .sel1      ( cfg_cmp_in1 ),
    .in0       ( cmp0_actual ),
    .in1       ( cmp0_verify )
);


cmp_verification CMP0 (
    .clk    ( clk ),
    .rst    ( rst ),
    .actual ( cmp0_actual ),
    .verify ( cmp0_verify ),
    .pass   ( cmp0_pass )
);

// Extend 1-bit to 4-bit for routing
assign cmp0_pass_ext = {3'b000, cmp0_pass};

// Output CB
cb_1out_generic CB_CMP_OUT (
    .tile_out    ( cmp0_pass_ext ),
    .sel         ( 2'b00 ),   // or cfg_cmp_out
    .track_drive ( cmp0_drive )
);
// ================= TILE PRIORITY MUX =================

// HC
assign hc0_from_tiles =
    (t0_drive  != 0) ? t0_drive  :
    (t24_drive != 0) ? t24_drive :
    (cmp0_drive!= 0) ? cmp0_drive:
    (t6_drive  != 0) ? t6_drive  :
    (t18_drive != 0) ? t18_drive :
    (t30_drive != 0) ? t30_drive :
    64'd0;

assign hc1_from_tiles =
    (t1_drive  != 0) ? t1_drive  :
    (t31_drive != 0) ? t31_drive :
    (t6_drive  != 0) ? t6_drive  :
    (t19_drive != 0) ? t19_drive :
    (t25_drive != 0) ? t25_drive :
    64'd0;

assign hc2_from_tiles =
    (t20_drive != 0) ? t20_drive :
    (t8_drive  != 0) ? t8_drive  :
    64'd0;

assign hc3_from_tiles =
    (t15_drive != 0) ? t15_drive :
    (t27_drive != 0) ? t27_drive :
    64'd0;

assign hc4_from_tiles =
    (t10_drive != 0) ? t10_drive :
    (t22_drive != 0) ? t22_drive :
    64'd0;

assign hc5_from_tiles =
    (t5_drive  != 0) ? t5_drive  :
    (t29_drive != 0) ? t29_drive :
    (t11_drive != 0) ? t11_drive :
    (t17_drive != 0) ? t17_drive :
    64'd0;


// VC
assign vc0_from_tiles =
    (div3_drive != 0) ? div3_drive :
    (sub2_drive != 0) ? sub2_drive :
    (ff4_drive  != 0) ? ff4_drive  :
    64'd0;

assign vc1_from_tiles =
    (ff9_drive != 0) ? ff9_drive : 64'd0;

assign vc2_from_tiles =
    (ff16_drive != 0) ? ff16_drive :
    (ff13_drive != 0) ? ff13_drive :
    (sub14_drive!= 0) ? sub14_drive:
    64'd0;

assign vc3_from_tiles =
    (ff21_drive != 0) ? ff21_drive :
    (ff23_drive != 0) ? ff23_drive :
    64'd0;

assign vc4_from_tiles =
    (ff26_drive != 0) ? ff26_drive :
    (ff28_drive != 0) ? ff28_drive :
    64'd0;

assign vc5_from_tiles =
    (ff34_drive != 0) ? ff34_drive :
    (div33_drive!= 0) ? div33_drive:
    (sub32_drive!= 0) ? sub32_drive:
    (ff35_drive != 0) ? ff35_drive :
    64'd0;
// Drive routing channel
//assign HC[(0*64)+63 : 0*64] = cmp0_drive;//hc0
//
//assign hc0_from_tiles = t0_drive | t24_drive | cmp0_drive|t6_drive|t18_drive|t30_drive;
////assign HC[(0*64)+63 : 0*64] =
//    //  hc0_from_io
//    //| hc0_from_tiles
//    //| sb_to_hc[(0*64)+63 : 0*64];
//
//assign hc1_from_tiles = t1_drive | t31_drive |t6_drive|t19_drive|t25_drive;
////assign HC[(1*64)+63 : 1*64] =
//    //  hc1_from_tiles
//    //| sb_to_hc[(1*64)+63 : 1*64];
//assign hc2_from_tiles = t20_drive |t8_drive;
////assign HC[(2*64)+63 : 2*64] =
//   //   hc2_from_tiles
//  //  | sb_to_hc[(2*64)+63 : 2*64];
//
//assign hc3_from_tiles = t15_drive | t27_drive;
////assign HC[(3*64)+63 : 3*64] =
//     // hc3_from_tiles
//    //| sb_to_hc[(3*64)+63 : 3*64];
//
//
//assign hc4_from_tiles = t10_drive | t22_drive;
////assign HC[(4*64)+63 : 4*64] =
//     // hc4_from_tiles
//   // | sb_to_hc[(4*64)+63 : 4*64];
//
//assign hc5_from_tiles = t5_drive | t29_drive |t11_drive|t17_drive;
////assign HC[(5*64)+63 : 5*64] =
//     // hc5_from_io
//   // | hc5_from_tiles
//    //| sb_to_hc[(5*64)+63 : 5*64];
//
//
//assign vc0_from_tiles = div3_drive | sub2_drive |ff4_drive;
////assign VC[(0*64)+63 : 0*64] =
//      //vc0_from_io
//    //| vc0_from_tiles
//   // | sb_to_vc[(0*64)+63 : 0*64];
//
//
//assign vc1_from_tiles = ff9_drive;
////assign VC[(1*64)+63 : 1*64] =
//     // vc1_from_tiles
//   // | sb_to_vc[(1*64)+63 : 1*64];
//
//
//
//assign vc2_from_tiles = ff16_drive | ff13_drive |  sub14_drive;
////assign VC[(2*64)+63 : 2*64] =
//     // vc2_from_tiles
//   // | sb_to_vc[(2*64)+63 : 2*64];
//
//
//assign vc3_from_tiles = ff21_drive | ff23_drive;
////assign VC[(3*64)+63 : 3*64] =
//     // vc3_from_tiles
//    //| sb_to_vc[(3*64)+63 : 3*64];
//
//assign vc4_from_tiles = ff26_drive|ff28_drive;
////assign VC[(4*64)+63 : 4*64] =
//   //   vc4_from_tiles
//   // | sb_to_vc[(4*64)+63 : 4*64];
//
//assign vc5_from_tiles = ff34_drive | div33_drive|sub32_drive |ff35_drive;
////a/ssign VC[(5*64)+63 : 5*64] =
//   //   vc5_from_io
//   // | vc5_from_tiles
//   // | sb_to_vc[(5*64)+63 : 5*64];



// ================= FIX: CHANNEL MUX =================
// ================= FINAL CHANNEL MUX =================

// HC
assign HC[63:0]   = (hc0_from_io != 0) ? hc0_from_io :
                    (hc0_from_tiles != 0) ? hc0_from_tiles :
                    hc0_from_sb;

assign HC[127:64] = (hc1_from_tiles != 0) ? hc1_from_tiles :
                    hc1_from_sb;

assign HC[191:128]= (hc2_from_tiles != 0) ? hc2_from_tiles :
                    hc2_from_sb;

assign HC[255:192]= (hc3_from_tiles != 0) ? hc3_from_tiles :
                    hc3_from_sb;

assign HC[319:256]= (hc4_from_tiles != 0) ? hc4_from_tiles :
                    hc4_from_sb;

assign HC[383:320]= (hc5_from_io != 0) ? hc5_from_io :
                    (hc5_from_tiles != 0) ? hc5_from_tiles :
                    hc5_from_sb;


// VC
assign VC[63:0]   = (vc0_from_io != 0) ? vc0_from_io :
                    (vc0_from_tiles != 0) ? vc0_from_tiles :
                    vc0_from_sb;

assign VC[127:64] = (vc1_from_tiles != 0) ? vc1_from_tiles :
                    vc1_from_sb;

assign VC[191:128]= (vc2_from_tiles != 0) ? vc2_from_tiles :
                    vc2_from_sb;

assign VC[255:192]= (vc3_from_tiles != 0) ? vc3_from_tiles :
                    vc3_from_sb;

assign VC[319:256]= (vc4_from_tiles != 0) ? vc4_from_tiles :
                    vc4_from_sb;

assign VC[383:320]= (vc5_from_io != 0) ? vc5_from_io :
                    (vc5_from_tiles != 0) ? vc5_from_tiles :
                    vc5_from_sb;

wire [3:0] io_cmp_out;

cb_1in_generic CB_IO_CMP (
    .track_bus ( HC[(0*64)+63 : 0*64] ), // same hc0
    .sel       ( cfg_io_sel[5:4] ),    
    .in0       ( io_cmp_out )
);
assign io_out[3:0] = io_cmp_out;
endmodule
