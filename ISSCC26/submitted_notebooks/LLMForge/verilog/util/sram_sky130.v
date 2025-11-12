module sram_sp_sky130 #(
    parameter   DATA_BIT = (`IDATA_WIDTH * `MAC_MULT_NUM),
    parameter   DEPTH = 128,
    parameter   ADDR_BIT = $clog2(DEPTH),
    parameter   BWE = 0 // bit write enable (currently unused)
)(
    input                       clk,
    input       [ADDR_BIT-1:0]  addr,
    input                       wen,   // active high write enable
    input       [DATA_BIT-1:0]  bwe,   // only used if BWE == 1
    input       [DATA_BIT-1:0]  wdata,
    input                       ren,   // active high read enable
    output  reg [DATA_BIT-1:0]  rdata
);

    // Constants
    localparam MACRO_WIDTH = 32;
    localparam MACRO_DEPTH = (DEPTH < 512) ? 128 : 512;

    localparam NUM_BANKS = DATA_BIT / MACRO_WIDTH;          
    localparam NUM_TILES = DEPTH / MACRO_DEPTH;             
    localparam TILE_ADDR_BITS = $clog2(MACRO_DEPTH);       
    localparam TILE_SEL_BITS = (NUM_TILES == 1) ? 1 : $clog2(NUM_TILES);  

    // localparam ADDR_WIDTH = $clog2(MACRO_DEPTH);   

    // Internal signals
    wire [TILE_ADDR_BITS-1:0] local_addr;
    wire [TILE_SEL_BITS-1:0]  tile_sel;

    // assign local_addr = (ADDR_BIT == TILE_ADDR_BITS) ? addr : addr[TILE_ADDR_BITS-1:0];
    // assign tile_sel   = (ADDR_BIT == TILE_ADDR_BITS) ? 1'b0 : addr[ADDR_BIT-1:TILE_ADDR_BITS];
    generate
        if (ADDR_BIT <= TILE_ADDR_BITS) begin
            assign tile_sel = {TILE_SEL_BITS{1'b0}};
        end else begin
            assign tile_sel = addr[ADDR_BIT-1:TILE_ADDR_BITS];
        end
        if (ADDR_BIT >= TILE_ADDR_BITS) begin
            assign local_addr = addr[TILE_ADDR_BITS-1:0];
        end else begin
            assign local_addr = {{(TILE_ADDR_BITS-ADDR_BIT){1'b0}}, addr};
        end
    endgenerate

    genvar bank, tile;
    // wire [MACRO_WIDTH-1:0] rdata_temp [0:NUM_BANKS-1];
    wire [DATA_BIT-1:0] tile_rdata_candidate [0:NUM_TILES-1];

    generate
    for (tile = 0; tile < NUM_TILES; tile = tile + 1) begin : tile_gen
        for (bank = 0; bank < NUM_BANKS; bank = bank + 1) begin : bank_gen
            // wire csb = ~(tile_sel == tile);
            // wire wsb = ~(wen);
            wire csb  = ~((tile_sel == tile) & (wen | ren));  // active low
            wire web  = ~((tile_sel == tile) & wen);
            wire [TILE_ADDR_BITS-1:0] addr0 = local_addr;
            wire [MACRO_WIDTH-1:0] din0  = wdata[bank*MACRO_WIDTH +: MACRO_WIDTH];
            wire [MACRO_WIDTH-1:0] dout0_t;

            if (DEPTH < 512) begin
                sky130_sram_0kbytes_1rw_32x128_32 sram_macro_32x128 (
                    .clk0(clk),
                    .csb0(csb),
                    .web0(web),
                    .addr0({1'b0,addr0}),
                    .din0(din0), 
                    .dout0(dout0_t)  
                );
            end else begin
                sky130_sram_2kbytes_1rw_32x512_32 sram_macro_32x512 (
                    .clk0(clk),
                    .csb0(csb),
                    .web0(web),
                    .addr0({1'b0,addr0}),
                    .din0(din0), 
                    .dout0(dout0_t) 
                );
            end

            assign tile_rdata_candidate[tile][bank*MACRO_WIDTH +: MACRO_WIDTH] = (ren & ~csb) ? dout0_t : 0;
        end
    end
    endgenerate

    // Read output mux
    always @(posedge clk) begin
        rdata <= tile_rdata_candidate[tile_sel];
    end

    // Read output mux
    // generate
    // for (genvar i = 0; i < NUM_BANKS; i = i + 1) begin : bank_write
    //     always @(posedge clk) begin
    //     rdata[i*MACRO_WIDTH +: MACRO_WIDTH] <= rdata_temp[i];
    //     end
    // end
    // endgenerate

endmodule


// OpenRAM SRAM model
// Words: 512
// Word size: 32

(* blackbox *)
module sky130_sram_0kbytes_1rw_32x128_32 (
    input  wire        clk0,
    input  wire        wen0,
    input  wire        csb0,
    input  wire [7:0]  addr0,
    input  wire [31:0] din0,
    output wire [31:0] dout0
);
endmodule

(* blackbox *)
module sky130_sram_2kbytes_1rw_32x512_32 (
    input  wire        clk0,
    input  wire        wen0,
    input  wire        csb0,
    input  wire [9:0]  addr0,
    input  wire [31:0] din0,
    output wire [31:0] dout0
);
endmodule

