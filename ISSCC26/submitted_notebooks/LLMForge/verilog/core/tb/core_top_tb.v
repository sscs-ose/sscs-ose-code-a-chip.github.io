`timescale 1ns / 1ps

module core_top_tb;

  // Parameters
  parameter MAC_MULT_NUM = ${mac_num};
  parameter IDATA_WIDTH = 8;
  parameter HEAD_CORE_NUM = 16;
  parameter KV_CACHE_DEPTH_SINGLE_USER = ${kv_cache_depth};
  parameter KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA = (KV_CACHE_DEPTH_SINGLE_USER*2);
  parameter CMEM_ADDR_WIDTH = (1 + ($clog2(MAC_MULT_NUM) +  $clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)));
  parameter GBUS_DATA_WIDTH = (MAC_MULT_NUM * IDATA_WIDTH);
  parameter GBUS_ADDR_WIDTH = (2 + $clog2(HEAD_CORE_NUM) + CMEM_ADDR_WIDTH);
  parameter CORE_MEM_ADDR_WIDTH = 14;
  parameter INTERFACE_DATA_WIDTH = 16;
  parameter MAX_NUM_USER = 1;
  parameter USER_ID_WIDTH = $clog2(MAX_NUM_USER);
  parameter RECOMPUTE_SCALE_WIDTH = 24;
  // Clocks & Reset
  reg clk = 0;
  reg rstn = 0;
  localparam CLK_PERIOD = ${clk_period};
  always #(CLK_PERIOD/2) clk = ~clk;

  // DUT inputs
  reg clean_kv_cache;
  reg [USER_ID_WIDTH-1:0] clean_kv_cache_user_id;
  reg [GBUS_ADDR_WIDTH-1:0] in_gbus_addr;
  reg in_gbus_wen;
  reg [GBUS_DATA_WIDTH-1:0] in_gbus_wdata;
  reg [INTERFACE_DATA_WIDTH-1:0] core_mem_wdata;
  reg [CORE_MEM_ADDR_WIDTH-1:0] core_mem_addr;
  reg core_mem_wen, core_mem_ren;
  reg op_cfg_vld, usr_cfg_vld, model_cfg_vld, pmu_cfg_vld, rc_cfg_vld;
  reg [40:0] op_cfg;
  reg [11:0] usr_cfg;
  reg [29:0] model_cfg;
  reg [3:0] pmu_cfg;
  reg [83:0] rc_cfg;
  reg control_state_update, start;
  reg [31:0] control_state;
  reg rc_scale_vld, rc_scale_clear;
  reg [RECOMPUTE_SCALE_WIDTH-1:0] rc_scale;
  reg vlink_data_in_vld;
  reg [GBUS_DATA_WIDTH-1:0] vlink_data_in;
  reg [GBUS_DATA_WIDTH-1:0] hlink_wdata;
  reg hlink_wen;

  // DUT outputs
  wire [GBUS_DATA_WIDTH-1:0] out_gbus_wdata;
  wire [GBUS_ADDR_WIDTH-1:0] out_gbus_addr;
  wire out_gbus_wen;
  wire finish;
  wire [INTERFACE_DATA_WIDTH-1:0] core_mem_rdata;
  wire core_mem_rvld;
  wire [GBUS_DATA_WIDTH-1:0] vlink_data_out;
  wire vlink_data_out_vld;
  wire [GBUS_DATA_WIDTH-1:0] hlink_rdata;
  wire hlink_rvalid;
  // Instantiate DUT
  core_top dut (
    .clk(clk),
    .rstn(rstn),
    .clean_kv_cache(clean_kv_cache),
    .clean_kv_cache_user_id(clean_kv_cache_user_id),
    .core_mem_addr(core_mem_addr),
    .core_mem_wdata(core_mem_wdata),
    .core_mem_wen(core_mem_wen),
    .core_mem_rdata(core_mem_rdata),
    .core_mem_ren(core_mem_ren),
    .core_mem_rvld(core_mem_rvld),
    .op_cfg_vld(op_cfg_vld),
    .op_cfg(op_cfg),
    .usr_cfg_vld(usr_cfg_vld),
    .usr_cfg(usr_cfg),
    .model_cfg_vld(model_cfg_vld),
    .model_cfg(model_cfg),
    .pmu_cfg_vld(pmu_cfg_vld),
    .pmu_cfg(pmu_cfg),
    .rc_cfg_vld(rc_cfg_vld),
    .rc_cfg(rc_cfg),
    .control_state(control_state),
    .control_state_update(control_state_update),
    .start(start),
    .finish(finish),
    .in_gbus_addr(in_gbus_addr),
    .in_gbus_wen(in_gbus_wen),
    .in_gbus_wdata(in_gbus_wdata),
    .out_gbus_addr(out_gbus_addr),
    .out_gbus_wen(out_gbus_wen),
    .out_gbus_wdata(out_gbus_wdata),
    .rc_scale(rc_scale),
    .rc_scale_vld(rc_scale_vld),
    .rc_scale_clear(rc_scale_clear),
    .vlink_data_in(vlink_data_in),
    .vlink_data_in_vld(vlink_data_in_vld),
    .vlink_data_out(vlink_data_out),
    .vlink_data_out_vld(vlink_data_out_vld),
    .hlink_wdata(hlink_wdata),
    .hlink_wen(hlink_wen),
    .hlink_rdata(hlink_rdata),
    .hlink_rvalid(hlink_rvalid)
  );

  // Simulation control
  initial begin
    $dumpfile("core_top.vcd");
    $dumpvars(0, core_top_tb);

    // Reset sequence
    rstn <= 0;
    #30 rstn <= 1;

    // Config setup
    op_cfg_vld <= 1;
    op_cfg <= {10'd32, 10'd1, 16'd0, 5'd9};
    usr_cfg_vld <= 1;
    usr_cfg <= 12'd0;
    model_cfg_vld <= 1;
    model_cfg <= 30'd0;
    pmu_cfg_vld <= 1;
    pmu_cfg <= 4'd0;
    rc_cfg_vld <= 1;
    rc_cfg <= 84'd0;

    // @(posedge clk);
    op_cfg_vld <= 0;
    usr_cfg_vld <= 0;
    model_cfg_vld <= 0;
    pmu_cfg_vld <= 0;
    rc_cfg_vld <= 0;

    // Start control FSM
    control_state <= 32'd1;
    control_state_update <= 1;
    start <= 1;
    // @(negedge clk);
    control_state_update <= 0;
    start <= 0;

    // Load weights
    in_gbus_wen <= 1;
    in_gbus_addr <= 0;
    in_gbus_wdata <= {MAC_MULT_NUM{8'h01}};
    @(negedge clk);
    in_gbus_wen <= 0;

    // Feed activation data
    vlink_data_in_vld <= 1;
    vlink_data_in <= {MAC_MULT_NUM{8'h10}};
    repeat (10) @(negedge clk);
    vlink_data_in_vld <= 0;

    // Trigger MAC pipeline
    control_state <= 32'd4;
    control_state_update <= 1;
    @(negedge clk);
    control_state_update <= 0;

    // Trigger recompute
    rc_scale <= 5'd4;
    rc_scale_vld <= 1;
    @(negedge clk);
    rc_scale_vld <= 0;

    // // Wait for finish or timeout
    // repeat (10000) @(negedge clk);
    // if (finish)
    //   $display("core_top completed");
    // else
    //   $display("Timeout!");
    repeat (1000) @(negedge clk);
    $finish;
  end

endmodule




module sky130_sram_0kbytes_1rw_32x128_32(
// `ifdef USE_POWER_PINS
//     vccd1,
//     vssd1,
// `endif
// Port 0: RW
    // clk0,csb0,web0,spare_wen0,addr0,din0,dout0
    clk0,csb0,web0,addr0,din0,dout0
);

parameter MACRO_WIDTH = 32 ;
parameter ADDR_WIDTH = 8 ;
parameter RAM_DEPTH = 1 << ADDR_WIDTH;
// FIXME: This delay is arbitrary.
parameter DELAY = 3 ;
parameter VERBOSE = 1 ; //Set to 0 to only display warnings
parameter T_HOLD = 1 ; //Delay to hold dout value after posedge. Value is arbitrary

`ifdef USE_POWER_PINS
    inout vccd1;
    inout vssd1;
`endif
input  clk0; // clock
input   csb0; // active low chip select
input  web0; // active low write control
input [ADDR_WIDTH-1:0]  addr0;
// input           spare_wen0; // spare mask
input [MACRO_WIDTH-1:0]  din0;
output [MACRO_WIDTH-1:0] dout0;

reg [MACRO_WIDTH-1:0]    mem [0:RAM_DEPTH-1];

reg  csb0_reg;
reg  web0_reg;
// reg spare_wen0_reg;
reg [ADDR_WIDTH-1:0]  addr0_reg;
reg [MACRO_WIDTH-1:0]  din0_reg;
reg [MACRO_WIDTH-1:0]  dout0;

// All inputs are registers
always @(posedge clk0)
begin
    csb0_reg = csb0;
    web0_reg = web0;
    // spare_wen0_reg = spare_wen0;
    addr0_reg = addr0;
    din0_reg = din0;
    // #(T_HOLD) dout0 = 32'bx;
    // if ( !csb0_reg && web0_reg && VERBOSE )
    //   $display($time," Reading %m addr0=%b dout0=%b",addr0_reg,mem[addr0_reg]);
    // if ( !csb0_reg && !web0_reg && VERBOSE )
    //   $display($time," Writing %m addr0=%b din0=%b",addr0_reg,din0_reg);
end


// Memory Write Block Port 0
// Write Operation : When web0 = 0, csb0 = 0
always @ (negedge clk0)
begin : MEM_WRITE0
    if ( !csb0_reg && !web0_reg ) begin
        mem[addr0_reg][31:0] = din0_reg[31:0];
        // if (spare_wen0_reg)
                // mem[addr0_reg][32] = din0_reg[32];
    end
end

// Memory Read Block Port 0
// Read Operation : When web0 = 1, csb0 = 0
always @ (negedge clk0)
begin : MEM_READ0
    if (!csb0_reg && web0_reg)
    //    dout0 <= #(DELAY) mem[addr0_reg];
    dout0 <= mem[addr0_reg];
end

endmodule

module sky130_sram_2kbytes_1rw_32x512_32(
// `ifdef USE_POWER_PINS
//     vccd1,
//     vssd1,
// `endif
// Port 0: RW
    // clk0,csb0,web0,spare_wen0,addr0,din0,dout0
    clk0,csb0,web0,addr0,din0,dout0
);

parameter MACRO_WIDTH = 32 ;
parameter ADDR_WIDTH = 10 ;
parameter RAM_DEPTH = 1 << ADDR_WIDTH;
// FIXME: This delay is arbitrary.
parameter DELAY = 3 ;
parameter VERBOSE = 1 ; //Set to 0 to only display warnings
parameter T_HOLD = 1 ; //Delay to hold dout value after posedge. Value is arbitrary

`ifdef USE_POWER_PINS
    inout vccd1;
    inout vssd1;
`endif
input  clk0; // clock
input   csb0; // active low chip select
input  web0; // active low write control
input [ADDR_WIDTH-1:0]  addr0;
// input           spare_wen0; // spare mask
input [MACRO_WIDTH-1:0]  din0;
output [MACRO_WIDTH-1:0] dout0;

reg [MACRO_WIDTH-1:0]    mem [0:RAM_DEPTH-1];

reg  csb0_reg;
reg  web0_reg;
// reg spare_wen0_reg;
reg [ADDR_WIDTH-1:0]  addr0_reg;
reg [MACRO_WIDTH-1:0]  din0_reg;
reg [MACRO_WIDTH-1:0]  dout0;

// All inputs are registers
always @(posedge clk0)
begin
    csb0_reg = csb0;
    web0_reg = web0;
    // spare_wen0_reg = spare_wen0;
    addr0_reg = addr0;
    din0_reg = din0;
    // #(T_HOLD) dout0 = 32'bx;
    // if ( !csb0_reg && web0_reg && VERBOSE )
    //   $display($time," Reading %m addr0=%b dout0=%b",addr0_reg,mem[addr0_reg]);
    // if ( !csb0_reg && !web0_reg && VERBOSE )
    //   $display($time," Writing %m addr0=%b din0=%b",addr0_reg,din0_reg);
end


// Memory Write Block Port 0
// Write Operation : When web0 = 0, csb0 = 0
always @ (negedge clk0)
begin : MEM_WRITE0
    if ( !csb0_reg && !web0_reg ) begin
        mem[addr0_reg][31:0] = din0_reg[31:0];
        // if (spare_wen0_reg)
                // mem[addr0_reg][32] = din0_reg[32];
    end
end

// Memory Read Block Port 0
// Read Operation : When web0 = 1, csb0 = 0
always @ (negedge clk0)
begin : MEM_READ0
    if (!csb0_reg && web0_reg)
    //    dout0 <= #(DELAY) mem[addr0_reg];
    dout0 <= mem[addr0_reg];
end

endmodule
