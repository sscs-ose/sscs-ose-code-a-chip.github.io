// Copyright (c) 2024, Saligane's Group at University of Michigan and Google Research
//
// Licensed under the Apache License, Version 2.0 (the "License");

// you may not use this file except in compliance with the License.

// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// =============================================================================
// Single port (SP) RAM with seperate wdata and rdata

module mem_sp #(
    parameter   DATA_BIT = 64,
    parameter   DEPTH = 1024,
    parameter   ADDR_BIT = $clog2(DEPTH),
    parameter   BWE = 0 //bit write enable
)(
    // Global Signals
    input                       clk,

    // Data Signals
    input       [ADDR_BIT-1:0]  addr,
    input                       wen,
    input       [DATA_BIT-1:0]  bwe,

    input       [DATA_BIT-1:0]  wdata,
    input                       ren,
    output  reg [DATA_BIT-1:0]  rdata
);



    // 1. RAM/Memory initialization
    reg [DATA_BIT-1:0]  mem [0:DEPTH-1];

    // 2. Write channel
generate
    if (BWE == 0) begin
        always @(posedge clk) begin
            if (wen) begin
                mem[addr] <= wdata;
            end
        end
    end
    else begin
        always @(posedge clk) begin
            if (wen) begin
                mem[addr] <= (wdata & bwe) | (mem[addr] & (~bwe));
            end
        end
    end
endgenerate

    // 3. Read channel
    always @(posedge clk) begin
        if (ren) begin
            rdata <= mem[addr];
        end
    end

endmodule

// =============================================================================
// Dual port (DP) RAM wrapper

module mem_dp #(
    parameter   DATA_BIT = 64,
    parameter   DEPTH = 1024,
    parameter   ADDR_BIT = $clog2(DEPTH),
    parameter   BWE =0
)(
    // Global Signals
    input                       clk,

    // Data Signals
    input       [ADDR_BIT-1:0]  waddr,
    input                       wen,
    input       [DATA_BIT-1:0]  wdata,
    input       [DATA_BIT-1:0]  bwe,
    input       [ADDR_BIT-1:0]  raddr,
    input                       ren,
    output  reg [DATA_BIT-1:0]  rdata
);

    // always @(negedge clk) begin
    // assert (!(wen && ren && (waddr == raddr))) 
    //     else $error("Error: Read and write addresses cannot be the same when both are enabled.");
    // end
 

    // 1, Memory initialization
    reg [DATA_BIT-1:0]  mem [0:DEPTH-1];

    // 2. Write channel
    // always @(posedge clk) begin
    //     if (wen) begin
    //         mem[waddr] <= wdata;
    //     end
    // end
    
    generate
    if (BWE == 0) begin
        always @(posedge clk) begin
            if (wen) begin
                mem[waddr] <= wdata;
            end
        end
    end
    else begin
        always @(posedge clk) begin
            if (wen) begin
                mem[waddr] <= (wdata & bwe) | (mem[waddr] & (~bwe));
            end
        end
    end
    endgenerate

    // 3. Read channel
    always @(posedge clk) begin
        if (ren) begin
            rdata <= mem[raddr];
        end
    end
    
endmodule


// =============================================================================
// Double-buffering (DB) RAM wrapper

module mem_db #(
    parameter   DATA_BIT = 64,
    parameter   DEPTH = 1024,
    parameter   ADDR_BIT = $clog2(DEPTH)
)(
    // Global signals
    input                       clk,

    // Control signals
    input                       sw,

    // Data signals
    input       [ADDR_BIT-1:0]  waddr,
    input                       wen,
    input       [DATA_BIT-1:0]  wdata,
    input       [ADDR_BIT-1:0]  raddr,
    input                       ren,
    output  reg [DATA_BIT-1:0]  rdata
);

    // 1. Interface declaration for SP memory bank
    reg     [ADDR_BIT-1:0]  bank0_addr;
    reg                     bank0_wen;
    reg     [DATA_BIT-1:0]  bank0_wdata;
    reg                     bank0_ren;
    wire    [DATA_BIT-1:0]  bank0_rdata;

    reg     [ADDR_BIT-1:0]  bank1_addr;
    reg                     bank1_wen;
    reg     [DATA_BIT-1:0]  bank1_wdata;
    reg                     bank1_ren;
    wire    [DATA_BIT-1:0]  bank1_rdata;

    reg                 read_sw;

    // 2. Memory initialization. Replace the SP-memory instance for simulation or synthesis
    mem_sp  #(.DATA_BIT(DATA_BIT), .DEPTH(DEPTH)) bank0 (
        .clk                (clk),
        .addr               (bank0_addr),
        .wen                (bank0_wen),
        .bwe                ({DATA_BIT{1'b0}}),
        .wdata              (bank0_wdata),
        .ren                (bank0_ren),
        .rdata              (bank0_rdata)
    );

    mem_sp  #(.DATA_BIT(DATA_BIT), .DEPTH(DEPTH)) bank1 (
        .clk                (clk),
        .addr               (bank1_addr),
        .wen                (bank1_wen),
        .bwe                ({DATA_BIT{1'b0}}),
        .wdata              (bank1_wdata),
        .ren                (bank1_ren),
        .rdata              (bank1_rdata)
    );

    // 3. Bank MUX
    always @(*) begin
        if (sw) begin   // sw = 1: Interface -> Bank0 (write), Bank1 (read) -> Interface
            bank0_addr = waddr;
            bank0_wen  = wen;
            bank0_ren  = 1'b0;
            bank1_addr = raddr;
            bank1_wen  = 1'b0;
            bank1_ren  = ren;
        end
        else begin      // sw = 0: Bank0 (read) -> Interface, Interface -> Bank1 (write)
            bank0_addr = raddr;
            bank0_wen  = 1'b0;
            bank0_ren  = ren;
            bank1_addr = waddr;
            bank1_wen  = wen;
            bank1_ren  = 1'b0;
        end
    end

    always @(*) begin
        bank0_wdata = wdata;
        bank1_wdata = wdata;
    end

    always @(posedge clk) begin
        read_sw <= sw;
    end

    always @(*) begin
        if (read_sw) begin   // sw = 1: Bank1 (read) -> Interface
            rdata = bank1_rdata;
        end
        else begin          // sw = 0: Bank0 (read) -> Interface
            rdata = bank0_rdata;
        end
    end

endmodule