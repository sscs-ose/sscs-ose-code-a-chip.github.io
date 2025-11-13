`timescale 1ns/1ps

module sram_sp_sky130_tb;

    // Parameters
    localparam DATA_BIT = ${sram_width};
    localparam DEPTH    = ${sram_depth};
    localparam real CLK_PERIOD = ${clk_period};  // Clock period in ns
    localparam ADDR_BIT = $clog2(DEPTH);

    // DUT signals
    reg                    clk;
    reg  [ADDR_BIT-1:0]    addr;
    reg                    wen;
    reg  [DATA_BIT-1:0]    wdata;
    reg  [DATA_BIT-1:0]    bwe;
    reg                    ren;
    wire [DATA_BIT-1:0]    rdata;

    // Instantiate the DUT
    //  mem_sp_sky130 #(
    //      .DATA_BIT(DATA_BIT),
    //      .DEPTH(DEPTH),
    //      .ADDR_BIT(ADDR_BIT),
    //      .BWE(0)
    //  ) dut (
    //      .clk(clk),
    //      .addr(addr),
    //      .wen(wen),
    //      .wdata(wdata),
    //      .bwe(bwe),
    //      .ren(ren),
    //      .rdata(rdata)
    //  );

    // for postsynthesis
   sram_sp_sky130 dut (
       .clk(clk),
       .addr(addr),
       .wen(wen),
       .wdata(wdata),
       .bwe(bwe),
       .ren(ren),
       .rdata(rdata)
   );

    // Clock generation
    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;  // 100MHz
    
    integer i;

    // Test procedure
    initial begin
        // --- VCD Dump ---
        $display("===== VCD Dump =====");
        $dumpfile("mem_sp_sky130.vcd");   // VCD output file name
        $dumpvars(0, sram_sp_sky130_tb);   // Dump all signals recursively under this module

        $display("===== Begin SRAM Testbench =====");
        addr = 0;
        wen  = 0;
        ren  = 0;
        wdata = 0;
        bwe = 1;

        repeat (5) @(posedge clk);  // Wait for initialization

        // Write to a few addresses
        for (i = 0; i < 8; i=i+1) begin
            @(posedge clk);
            addr  <= i;
            wdata <= $random;
            wen   <= 0; // pre-set

            @(posedge clk);
            wen   <= 1;  // activate write
            @(posedge clk);
            wen   <= 0;  // deactivate
            $display("[WRITE] addr=%0d data=0x%h", i, wdata);
        end

        @(posedge clk);
        wen <= 0;

        // Read back the values
        for (i = 0; i < 8; i=i+1) begin
            @(posedge clk);
            addr <= i;
            ren  <= 1;

            @(posedge clk);
            @(posedge clk); // capture rdata at correct timing
            @(negedge clk);
            $display("[READ ] addr=%0d data=0x%h", i, rdata);
        end

        // // Write to the whole sram
        // for (i = 0; i < DEPTH; i=i+1) begin
        //     @(posedge clk);
        //     addr  <= i;
        //     wdata <= $random;
        //     wen   <= 1; 
        //     ren   <= 0; 
        // end

        // // Read back the values
        // for (i = 0; i < DEPTH; i=i+1) begin
        //     @(posedge clk);
        //     addr  <= i;
        //     wdata <= $random;
        //     wen   <= 0; 
        //     ren   <= 1; 
        // end

        repeat (100) @(posedge clk);  // Wait for initialization
        
        $display("===== SRAM Test Completed =====");
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
