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

// Series to Parallel

module align_s2p #(
    parameter   IDATA_WIDTH = 64,
    parameter   ODATA_BIT = 256
)(
    // Global Signals
    input                       clk,
    input                       rstn, //jdamle change - was rst

    // Data Signals
    input       [IDATA_WIDTH-1:0] idata,
    input                       idata_valid,
    output  reg [ODATA_BIT-1:0] odata,
    output  reg                 odata_valid
);

    localparam  REG_NUM = ODATA_BIT / IDATA_WIDTH;
    localparam  ADDR_BIT = $clog2(REG_NUM+1);

    // 1. Register file / buffer
    reg     [IDATA_WIDTH-1:0] regfile [0:REG_NUM-1];
    reg     [ADDR_BIT-1:0]  regfile_addr;           

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            regfile_addr <= 'd0;
        end
        else if (idata_valid) begin
            regfile_addr <= (regfile_addr + 1'b1)%REG_NUM;
        end
    end

    always @(posedge clk) begin
        if (idata_valid) begin
            regfile[regfile_addr] <= idata;
        end
    end

    // 2. Output
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            odata_valid <= 1'b0;
        end
        else begin
            if ((regfile_addr==REG_NUM-1) && idata_valid) begin
                odata_valid <= 1'b1;
            end
            else begin
                odata_valid <= 1'b0;
            end
        end
    end

    genvar i;
    generate
        for (i = 0; i < REG_NUM; i = i + 1) begin:gen_pal
            always @(*) begin
                odata[i*IDATA_WIDTH+:IDATA_WIDTH] = regfile[i];
            end
        end
    endgenerate
    
endmodule

// =============================================================================
// Parallel to Series

module align_p2s #(
    parameter   IDATA_WIDTH = 256,
    parameter   ODATA_BIT = 64
)(
    // Global Signals
    input                       clk,
    input                       rstn,

    // Data Signals
    input       [IDATA_WIDTH-1:0] idata,
    input                       idata_valid,
    output  reg [ODATA_BIT-1:0] odata,
    output  reg                 odata_valid
);

    localparam  REG_NUM = IDATA_WIDTH / ODATA_BIT;
    localparam  ADDR_BIT = $clog2(REG_NUM);

    // 1. Register File / Buffer
    reg     [ODATA_BIT-1:0] regfile [0:REG_NUM-1];
    reg     [ADDR_BIT-1:0]  regfile_addr;
    reg                     regfile_valid;

    genvar i;
    generate
        for (i = 0; i < REG_NUM; i = i + 1) begin: gen_ser
            always @(posedge clk or negedge rstn) begin
                if (!rstn) begin
                    regfile[i] <= 'd0;
                end
                else if (idata_valid) begin
                    regfile[i] <= idata[i*ODATA_BIT+:ODATA_BIT];
                end
            end
        end
    endgenerate

    // 2. FSM: segment counter
    parameter   REGFILE_IDLE  = 2'b01,
                REGFILE_VALID = 2'b10;
    reg     [1:0]   regfile_state;

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            regfile_state <= 'd0;
            regfile_valid <= 1'b0;
            regfile_addr  <= 'd0;
        end
        else begin
            case (regfile_state)
                REGFILE_IDLE: begin
                    if (idata_valid) begin
                        regfile_state <= REGFILE_VALID;
                        regfile_addr  <= 'd0;
                        regfile_valid <= 1'b1;
                    end
                end
                REGFILE_VALID: begin
                    if (regfile_addr == REG_NUM - 1'b1) begin
                        if (idata_valid) begin
                            regfile_state <= REGFILE_VALID;
                            regfile_addr  <= 'd0;
                            regfile_valid <= 1'b1;
                        end
                        else begin
                            regfile_state <= REGFILE_IDLE;
                            regfile_addr  <= 'd0;
                            regfile_valid <= 1'b0;
                        end
                    end
                    else begin
                        regfile_addr <= regfile_addr + 1'b1;
                    end
                end
                default: begin
                    regfile_state <= REGFILE_IDLE;
                    regfile_addr  <= 'd0;
                    regfile_valid <= 1'b0;
                end
            endcase
        end
    end

    // 3. Output
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            odata <= 'd0;
        end
        else if (regfile_valid) begin
            odata <= regfile[regfile_addr];
        end
    end

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            odata_valid <= 1'b0;
        end
        else begin
            odata_valid <= regfile_valid;
        end
    end

endmodule