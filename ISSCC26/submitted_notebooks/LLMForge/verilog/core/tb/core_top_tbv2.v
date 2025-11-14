// -----------------------------------------------------------------------------
// tb_core_top_ppa_v.v  (Verilog-2001)
// - Exact cycle counting per stage using core_top.start/finish
// - VCD gated during the active work window
// - +args: CLKPS, WARM, COOL, TIMEOUT, SEED
// - Optional CMEM preload via in_gbus writes
// -----------------------------------------------------------------------------
`timescale 1ns / 1ps
module core_top_tb;

  // -----------------------
  // Clock / Reset
  // -----------------------
  localparam real CLK_PERIOD_NS = ${clk_period};  // default 200 MHz
  real CLK_PERIOD_PS = CLK_PERIOD_NS * 1000.0;
  reg clk = 1'b0;
  always #(CLK_PERIOD_NS/2) clk = ~clk;

  reg rstn;

  // -----------------------
  // Widths & fallbacks
  // -----------------------
  // Prefer macros from sys_defs.svh. If a macro is missing, we fall back to 32-bit.
localparam USER_ID_W = 2;

localparam CORE_MEM_ADDR_W = (${mac_num}*8);

// core_top expects INTERFACE_DATA_WIDTH for core_mem data ports
localparam CORE_MEM_DATA_W = (${mac_num}*8);

localparam BUS_CMEM_ADDR_WIDTH = 13;
localparam CMEM_ADDR_WIDTH = 1 + $clog2(${kv_cache_depth}) + $clog2(${mac_num});
localparam BUS_CORE_ADDR_WIDTH = 4;
localparam HEAD_SRAM_BIAS_WIDTH = 2;
localparam GBUS_ADDR_W = ((HEAD_SRAM_BIAS_WIDTH + BUS_CORE_ADDR_WIDTH) + BUS_CMEM_ADDR_WIDTH);

localparam GBUS_DATA_W = (${mac_num}*8);

localparam RC_SCALE_W = 24;

localparam LANES_W = (${mac_num}*8);


  // -----------------------
  // DUT I/O (mirrors core_top.v)
  // -----------------------
  reg                          clean_kv_cache;
  reg  [USER_ID_W-1:0]         clean_kv_cache_user_id;

  reg  [CORE_MEM_ADDR_W-1:0]   core_mem_addr;
  reg  [CORE_MEM_DATA_W-1:0]   core_mem_wdata;
  reg                          core_mem_wen;
  wire [CORE_MEM_DATA_W-1:0]   core_mem_rdata;
  reg                          core_mem_ren;
  wire                         core_mem_rvld;

  reg                          op_cfg_vld;
  reg  [40:0]                  op_cfg;
  reg                          usr_cfg_vld;
  reg  [11:0]                  usr_cfg;
  reg                          model_cfg_vld;
  reg  [29:0]                  model_cfg;
  reg                          pmu_cfg_vld;
  reg  [3:0]                   pmu_cfg;
  reg                          rc_cfg_vld;
  reg  [83:0]                  rc_cfg;

  reg  [31:0]                  control_state;
  reg                          control_state_update;

  reg                          start;
  wire                         finish;

  // In/Out GBUS
  reg  [GBUS_ADDR_W-1:0]       in_gbus_addr;
  reg                          in_gbus_wen;
  reg  [GBUS_DATA_W-1:0]       in_gbus_wdata;
  wire [GBUS_ADDR_W-1:0]       out_gbus_addr;
  wire                         out_gbus_wen;
  wire [GBUS_DATA_W-1:0]       out_gbus_wdata;

  // RC (recompute)
  reg  [RC_SCALE_W-1:0]        rc_scale;
  reg                          rc_scale_vld;
  reg                          rc_scale_clear;

  // Links
  reg  [LANES_W-1:0]           vlink_data_in;
  reg                          vlink_data_in_vld;
  wire [LANES_W-1:0]           vlink_data_out;
  wire                         vlink_data_out_vld;

  reg  [LANES_W-1:0]           hlink_wdata;
  reg                          hlink_wen;
  wire [LANES_W-1:0]           hlink_rdata;
  wire                         hlink_rvalid;

  // -----------------------
  // Instantiate DUT
  // -----------------------
  core_top dut (
    .clk(clk), .rstn(rstn),

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

  // -----------------------
  // Stage codes (match your RTL/tbv2)
  // -----------------------
  localparam [31:0] S_IDLE   = 32'd0;
  localparam [31:0] S_Q_GEN  = 32'd1;
  localparam [31:0] S_K_GEN  = 32'd2;
  localparam [31:0] S_V_GEN  = 32'd3;
  localparam [31:0] S_ATT_QK = 32'd4;
  localparam [31:0] S_ATT_PV = 32'd5;
  localparam [31:0] S_PROJ   = 32'd6;
  localparam [31:0] S_FFN0   = 32'd7;
  localparam [31:0] S_FFN1   = 32'd8;

  // -----------------------
  // VCD
  // -----------------------
  initial begin
    $dumpfile("core_top.vcd");
    $dumpvars(0, dut);
    $dumpoff;
  end

  // -----------------------
  // Plusargs & settings
  // -----------------------
  integer warm_cycles   = 10;
  integer cool_cycles   = 10;
  integer TIMEOUT_CYC   = 100;
  integer SEED          = 1;

  initial begin
    if ($value$plusargs("WARM=%d",  warm_cycles)) ;
    if ($value$plusargs("COOL=%d",  cool_cycles)) ;
    if ($value$plusargs("CLKPS=%f", CLK_PERIOD_PS)) ;
    if ($value$plusargs("SEED=%d",  SEED)) ;
    if ($value$plusargs("TIMEOUT=%d", TIMEOUT_CYC)) ;
    $display("[TB] CLK=%0.2f MHz  WARM=%0d  COOL=%0d  TIMEOUT=%0d  SEED=%0d",
             1e6/CLK_PERIOD_PS, warm_cycles, cool_cycles, TIMEOUT_CYC, SEED);
  end

  // -----------------------
  // Reset & defaults
  // -----------------------
  task reset_dut;
    integer i;
    begin
      rstn = 1'b0;

      clean_kv_cache = 1'b0;
      clean_kv_cache_user_id = {2'b0};

      core_mem_addr = {CORE_MEM_ADDR_W{1'b0}};
      core_mem_wdata= {CORE_MEM_DATA_W{1'b0}};
      core_mem_wen  = 1'b0;
      core_mem_ren  = 1'b0;

      op_cfg_vld=1'b0;  op_cfg=41'd0;
      usr_cfg_vld=1'b0; usr_cfg=12'd0;
      model_cfg_vld=1'b0; model_cfg=30'd0;
      pmu_cfg_vld=1'b0;  pmu_cfg=4'd0;
      rc_cfg_vld=1'b0;   rc_cfg=84'd0;

      control_state = S_IDLE; control_state_update = 1'b0;
      start = 1'b0;

      in_gbus_addr={GBUS_ADDR_W{1'b0}};
      in_gbus_wen=1'b0;
      in_gbus_wdata={GBUS_DATA_W{1'b0}};

      rc_scale={RC_SCALE_W{1'b0}};
      rc_scale_vld=1'b0;
      rc_scale_clear=1'b0;

      vlink_data_in={LANES_W{1'b0}};
      vlink_data_in_vld=1'b0;
      hlink_wdata={LANES_W{1'b0}};
      hlink_wen=1'b0;

      for (i=0;i<10;i=i+1) @(posedge clk);
      rstn = 1'b1;
      for (i=0;i<10;i=i+1) @(posedge clk);
    end
  endtask

  // -----------------------
  // Helpers
  // -----------------------
  function [40:0] make_op_cfg;
    input integer acc_num;
    input integer scale;
    input integer bias;
    input integer shift;
    reg [40:0] x;
    begin
      x = 41'd0;
      x[40:31] = acc_num[9:0];
      x[30:21] = scale[9:0];
      x[20:5]  = bias[15:0];
      x[4:0]   = shift[4:0];
      make_op_cfg = x;
    end
  endfunction

  task push_state;
    input [31:0] st;
    begin
      control_state        <= st;
      control_state_update <= 1'b1;
      @(posedge clk);
      control_state_update <= 1'b0;
      @(posedge clk);
    end
  endtask

  task drive_links;
    input integer cycles_i;
  integer i;
  integer _rand_seed;
    begin
      for (i=0;i<cycles_i;i=i+1) begin
        hlink_wen         <= ((i%3)==0);
    _rand_seed = SEED;
    hlink_wdata       <= $random(_rand_seed);
    vlink_data_in_vld <= ((i%5)==0);
    _rand_seed = SEED ^ i;
    vlink_data_in     <= $random(_rand_seed);
        @(posedge clk);
      end
      hlink_wen <= 1'b0;
      vlink_data_in_vld <= 1'b0;
    end
  endtask

  task poke_rc_scale;
    input integer pulses;
    input integer gap;
    integer i,j;
  integer _rand_seed;
    begin
      for (i=0;i<pulses;i=i+1) begin
    _rand_seed = SEED + i;
    rc_scale     <= $random(_rand_seed);
        rc_scale_vld <= 1'b1;
        @(posedge clk);
        rc_scale_vld <= 1'b0;
        for (j=0;j<gap;j=j+1) @(posedge clk);
      end
    end
  endtask

  // in_gbus CMEM preload
  task preload_cmem;
    input integer words;
    integer i;
  integer _rand_seed;
    begin
      for (i=0;i<words;i=i+1) begin
        // If your address mapping differs, adjust here.
        in_gbus_addr  = { { (GBUS_ADDR_W>0)?GBUS_ADDR_W:1 {1'b0} } };
        in_gbus_addr[ (CMEM_ADDR_WIDTH>0)?(CMEM_ADDR_WIDTH-1):0 : 0 ] = i[CMEM_ADDR_WIDTH-1:0];
    _rand_seed = SEED + i;
    in_gbus_wdata = $random(_rand_seed);
        in_gbus_wen   = 1'b1;
        @(posedge clk);
        in_gbus_wen   = 1'b0;
        @(posedge clk);
      end
    end
  endtask

  // -----------------------
  // Cycle counter (64-bit)
  // -----------------------
  reg [63:0] cycles;
  always @(posedge clk or negedge rstn) begin
    if (!rstn) cycles <= 64'd0;
    else       cycles <= cycles + 64'd1;
  end

  // -----------------------
  // Lightweight TB monitor (prints key events / progress)
  // -----------------------
  localparam DEBUG_TB = 1;
  reg prev_start = 1'b0;
  reg prev_finish = 1'b0;

  always @(posedge clk) begin
    if (DEBUG_TB) begin
      // notify start/finish edges
      if (start & ~prev_start) $display("[TB][START]  %0t ps  cycles=%0d", $time, cycles);
      if (finish & ~prev_finish) $display("[TB][FINISH] %0t ps  cycles=%0d", $time, cycles);

      // bus / mem events
      if (in_gbus_wen)    $display("[TB][GBUS_IN]  %0t ps addr=%0h data=%0h", $time, in_gbus_addr, in_gbus_wdata);
      if (out_gbus_wen)   $display("[TB][GBUS_OUT] %0t ps addr=%0h data=%0h", $time, out_gbus_addr, out_gbus_wdata);

      if (core_mem_wen)   $display("[TB][CMEM_WR]  %0t ps addr=%0h data=%0h", $time, core_mem_addr, core_mem_wdata);
      if (core_mem_ren & core_mem_rvld) $display("[TB][CMEM_RD]  %0t ps addr=%0h data=%0h", $time, core_mem_addr, core_mem_rdata);

      if (vlink_data_out_vld) $display("[TB][VLINK_OUT] %0t ps data=%0h", $time, vlink_data_out);
      if (hlink_wen)         $display("[TB][HLINK_WR]  %0t ps data=%0h", $time, hlink_wdata);

      // rc_scale events
      if (rc_scale_vld) $display("[TB][RC_SCALE]  %0t ps scale=%0h", $time, rc_scale);

      // periodic progress message
      if ((cycles % 1000) == 0) $display("[TB][PROG] %0t ps cycles=%0d", $time, cycles);

      // update previous-state trackers
      prev_start <= start;
      prev_finish <= finish;
    end
  end

  // -----------------------
  // Measure one stage
  // -----------------------
  task measure_stage;
    input [159:0] tag;
    input [31:0]  st_code;
    input integer warm;
    input integer cool;
    reg [63:0] cyc0, cyc1;
    integer watchdog;
    begin
      push_state(st_code);

      // Warm “background” activity
      drive_links(warm/2);
      poke_rc_scale(2, 3);
      drive_links(warm - (warm/2));

      @(posedge clk);
      cyc0 = cycles;

      $display("[TB] VCD  ON   %0s @ %0t ps", tag, $time);
      $dumpon;

      // Start the stage
      start <= 1'b1; @(posedge clk); start <= 1'b0;

      // Wait for finish or timeout
      watchdog = 0;
      while (finish == 1'b0 && watchdog < TIMEOUT_CYC) begin
        @(posedge clk);
        watchdog = watchdog + 1;
      end

      cyc1 = cycles;
      $dumpoff;
      $display("[TB] VCD  OFF  %0s @ %0t ps", tag, $time);

      if (watchdog >= TIMEOUT_CYC) begin
        $display("[TB][ERROR] TIMEOUT in stage %0s (no finish in %0d cycles)", tag, TIMEOUT_CYC);
      end else begin
        $display("[TB] STAGE %-6s cycles=%0d", tag, (cyc1 - cyc0));
      end

      // Cooldown
      drive_links(cool);
    end
  endtask

  // -----------------------
  // Test sequence
  // -----------------------
  initial begin
    reset_dut();

    // Minimal plausible configs
    op_cfg      = make_op_cfg(16, 1, 0, 0);
    op_cfg_vld  = 1'b1; @(posedge clk); op_cfg_vld = 1'b0;

    usr_cfg     = 12'd0;  usr_cfg_vld   = 1'b1; @(posedge clk); usr_cfg_vld   = 1'b0;
    model_cfg   = 30'd0;  model_cfg_vld = 1'b1; @(posedge clk); model_cfg_vld = 1'b0;
    pmu_cfg     = 4'd0;   pmu_cfg_vld   = 1'b1; @(posedge clk); pmu_cfg_vld   = 1'b0;
    rc_cfg      = 84'd0;  rc_cfg_vld    = 1'b1; @(posedge clk); rc_cfg_vld    = 1'b0;

    // Optional: preload some CMEM content
`ifdef CMEM_ADDR_WIDTH
    preload_cmem(64);
`endif

    // Sequence through stages; you can comment out the ones you don't need
    measure_stage("Q_GEN",  S_Q_GEN,  warm_cycles, cool_cycles);
    measure_stage("K_GEN",  S_K_GEN,  warm_cycles, cool_cycles);
    measure_stage("V_GEN",  S_V_GEN,  warm_cycles, cool_cycles);
    measure_stage("ATT_QK", S_ATT_QK, warm_cycles, cool_cycles);
    measure_stage("ATT_PV", S_ATT_PV, warm_cycles, cool_cycles);
    measure_stage("PROJ",   S_PROJ,   warm_cycles, cool_cycles);
    measure_stage("FFN0",   S_FFN0,   warm_cycles, cool_cycles);
    measure_stage("FFN1",   S_FFN1,   warm_cycles, cool_cycles);

    $display("\n[TB] Done. VCD windows match active work. Check core_top_ppa.vcd.");
    #(10*CLK_PERIOD_PS) $finish;
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

