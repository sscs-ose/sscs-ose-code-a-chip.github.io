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
// Accumulation Top Module

module core_acc #(
    parameter   IDATA_WIDTH = `ODATA_WIDTH, // Set a Higher Bitwidth for Accumulation
    parameter   ODATA_BIT = `ODATA_WIDTH,
    parameter   CDATA_ACCU_NUM_WIDTH = `CDATA_ACCU_NUM_WIDTH
)(
    // Global Signals
    input                                       clk,
    input                                       rstn,

    // Global Config Signals
    input       [CDATA_ACCU_NUM_WIDTH-1:0]      cfg_acc_num,

    // Data Signals
    input       [IDATA_WIDTH-1:0]               idata,
    input                                       idata_valid,
    output   signed   [ODATA_BIT-1:0]           odata,
    output                                      odata_valid
);

    // Accumulation Counter
    wire    finish;

    core_acc_ctrl   #(.CDATA_ACCU_NUM_WIDTH(CDATA_ACCU_NUM_WIDTH)) acc_counter_inst (
        .clk                (clk),
        .rstn               (rstn),
        .cfg_acc_num        (cfg_acc_num),
        .psum_valid         (idata_valid),
        .psum_finish        (finish)
    );

    // Accumulation Logic
    core_acc_mac    #(.IDATA_WIDTH(IDATA_WIDTH), .ODATA_BIT(ODATA_BIT)) acc_mac_inst (
        .clk                (clk),
        .rstn               (rstn),
        .finish             (finish),

        .idata              (idata),
        .idata_valid        (idata_valid),
        .odata              (odata),
        .odata_valid        (odata_valid)
    );

endmodule

// =============================================================================
// FSM for Accumulation Counter

module core_acc_ctrl #(
    parameter   CDATA_ACCU_NUM_WIDTH = 8
)(
    // Global Signals
    input                       clk,
    input                       rstn,

    // Config Signals
    input       [CDATA_ACCU_NUM_WIDTH-1:0] cfg_acc_num,

    // Control Signals
    input                       psum_valid,
    output  reg                 psum_finish
);


    reg     [CDATA_ACCU_NUM_WIDTH-1:0] psum_cnt;

always @(posedge clk or negedge rstn) begin
    if(~rstn)begin
        psum_cnt <= 0;
    end
    else if(psum_valid && psum_cnt == cfg_acc_num - 1&& cfg_acc_num != 0) begin
        psum_cnt <= 0;
    end
    else if(psum_valid)begin
        psum_cnt <= psum_cnt + 1;
    end
end

always @(posedge clk or negedge rstn) begin
    if(~rstn)begin
        psum_finish <= 0;
    end
    else if(psum_valid && psum_cnt == cfg_acc_num - 1 && cfg_acc_num != 0) begin
        psum_finish <= 1;
    end
    else begin
        psum_finish <= 0;
    end
end

endmodule

// =============================================================================
// Computing Logic in Accumulation

module core_acc_mac #(
    parameter   IDATA_WIDTH = 32, 
    parameter   ODATA_BIT = 32  // Note: ODATA_BIT >= IDATA_WIDTH
)(
    // Global Signals
    input                       clk,
    input                       rstn,

    // Control Signals
    input                       finish,

    // Data Signals
    input       [IDATA_WIDTH-1:0]   idata,
    input                           idata_valid,
    output  reg [ODATA_BIT-1:0]     odata,
    output  reg                     odata_valid
);
    // Accumulation
    reg signed  [ODATA_BIT-1:0] acc_reg;

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            acc_reg <= 'd0;
        end
        else if (finish) begin
            if(idata_valid)
                acc_reg <= idata;
            else
                acc_reg <= '0;
        end
        else if (idata_valid) begin
            acc_reg <= idata + acc_reg;
        end
    end

    // Output and Valid
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            odata <= 'd0;
        end
        else if (finish) begin
            odata <= acc_reg;
        end
    end

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            odata_valid <= 1'b0;
        end
        else begin
            odata_valid <= finish;
        end
    end

endmodule 